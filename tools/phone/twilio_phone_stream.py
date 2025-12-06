import asyncio
import json
import base64
import logging
import time
from fastapi import WebSocket
from typing import Dict, Any, Optional

import webrtcvad

from tools import SpeechToTextTool, ConversationalResponseTool, TextToSpeechTool
from tools.phone.audio_utils import convert_pcm_to_mulaw, convert_mulaw_to_wav_bytes
from conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

# VAD configuration
VAD_AGGRESSIVENESS = 3
VAD_SAMPLE_RATE = 8000  # Twilio media stream is 8kHz mu-law
VAD_FRAME_DURATION_MS = 20
VAD_FRAME_BYTES = (VAD_SAMPLE_RATE * VAD_FRAME_DURATION_MS // 1000)

class TwilioStreamHandler:
    """Handles the real-time Twilio media stream for a single phone call."""

    def __init__(self, websocket: WebSocket, speech_tool: SpeechToTextTool, tts_tool: TextToSpeechTool, conversation_tool: ConversationalResponseTool, agent_config: Optional[Dict[str, Any]] = None):
        self.websocket = websocket
        self.speech_tool = speech_tool
        self.tts_tool = tts_tool
        self.conversation_tool = conversation_tool
        self.agent_config = agent_config  # Store agent configuration
        self.is_outbound_call = False  # Track if this is an outbound call
        
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.speech_buffer = bytearray()
        self.is_speaking = False  # User is speaking
        self.ai_is_speaking = False  # AI is speaking (prevents feedback loop)
        self.interrupt_detected = False  # User interrupted AI
        self.tts_streaming_task = None  # Track active TTS streaming task for cancellation
        self.ai_speech_start_time = None  # Timestamp when AI started speaking (for grace period)
        self.stream_sid = None
        self.call_sid = None
        self.to_number = None  # Store To number for credential lookup
        self.session_id = None
        self.session_data: Dict[str, Any] = {}
        self.silence_frames_count = 0
        self.speech_frames_count = 0
        self.interrupt_speech_frames = 0  # Track how many frames of speech during interrupt (to validate real interrupt)
        self.SILENCE_THRESHOLD_FRAMES = 25  # 25 frames * 20ms/frame = 500ms of silence to trigger processing
        self.INTERRUPT_GRACE_PERIOD_MS = 1200  # Wait 1200ms after AI starts speaking before allowing interrupts (prevents feedback loop)
        self.MIN_INTERRUPT_FRAMES = 10  # Require at least 10 frames (200ms) of sustained speech for valid interrupt
        self.speech_processing_lock = asyncio.Lock()  # Prevent concurrent speech processing
        self.speech_processing_task = None  # Track active speech processing task for cancellation
        self.query_sequence = 0  # Track query sequence to ensure we process the most recent

    async def handle_stream(self):
        """Main loop to receive and process audio from the Twilio media stream."""
        logger.info("New Twilio stream connection handler created.")
        while True:
            message = await self.websocket.receive_text()
            data = json.loads(message)

            event = data.get('event')
            if event == 'start':
                await self._handle_start_event(data['start'])
                # Asynchronously send the greeting message (only if agent_config was loaded)
                if self.agent_config:
                    call_type = "OUTBOUND" if self.is_outbound_call else "INBOUND"
                    logger.info(f"✅ Agent config loaded, scheduling greeting for {call_type} call {self.call_sid}")
                    # For outbound calls, send greeting immediately to drive the conversation
                    if self.is_outbound_call:
                        logger.info(f"🚀 Outbound call: AI will speak first to drive the conversation")
                    asyncio.create_task(self._send_greeting())
                else:
                    logger.warning(f"⚠️ Agent config not loaded, skipping greeting for call {self.call_sid}")
            elif event == 'media':
                self._process_media_event(data['media'])
            elif event == 'stop':
                self._handle_stop_event(data['stop'])
                break
            elif event == 'mark':
                mark_name = data['mark']['name']
                logger.info(f"Received mark event: {mark_name}")
                # When AI finishes speaking, re-enable user audio processing
                if mark_name == "end_of_ai_speech":
                    was_interrupted = self.interrupt_detected
                    self.ai_is_speaking = False
                    self.ai_speech_start_time = None
                    self.interrupt_speech_frames = 0  # Reset interrupt tracking
                    logger.info("✅ AI finished speaking, listening for user now.")
                    # If there's waiting interrupt speech, process it immediately
                    if was_interrupted and self.is_speaking and self.speech_buffer:
                        logger.info("🔄 AI stopped, processing waiting interrupt speech...")
                        
                        # CRITICAL: Cancel previous task before starting new one
                        if self.speech_processing_task and not self.speech_processing_task.done():
                            logger.info("⏳ Cancelling previous query before processing interrupt...")
                            self.speech_processing_task.cancel()
                        
                        # Increment query sequence AFTER cancelling previous task
                        self.query_sequence += 1
                        logger.info(f"🆕 Starting Interrupt Query #{self.query_sequence}")
                        self.speech_processing_task = asyncio.create_task(self._process_waiting_interrupt())

    async def _handle_start_event(self, start_data: Dict):
        """Handles the 'start' event from Twilio stream."""
        self.stream_sid = start_data['streamSid']
        self.call_sid = start_data['callSid']
        custom_params = start_data.get('customParameters', {})
        from_number = custom_params.get('From', 'Unknown')
        to_number = custom_params.get('To', 'Unknown')
        agent_phone_number = custom_params.get('AgentPhoneNumber')  # For outbound calls
        is_outbound = custom_params.get('IsOutbound', 'false').lower() == 'true'
        self.is_outbound_call = is_outbound  # Store for later use
        self.to_number = to_number  # Store for credential lookup
        
        logger.info(f"Stream started: call_sid={self.call_sid}, stream_sid={self.stream_sid}")
        logger.info(f"Call from: {from_number} to: {to_number}")
        if is_outbound:
            logger.info(f"📤 Detected OUTBOUND call in stream handler - AI will drive the conversation")
        
        # Check for Scheduled Call ID (Priority 1)
        scheduled_call_id = custom_params.get('ScheduledCallId')
        if not self.agent_config and scheduled_call_id:
            try:
                logger.info(f"🗓️ Loading config from Scheduled Call ID: {scheduled_call_id}")
                from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
                scheduled_store = MongoDBScheduledCallStore()
                scheduled_call = await scheduled_store.get_scheduled_call(scheduled_call_id)
                
                if scheduled_call:
                    # Construct virtual agent config
                    self.agent_config = {
                        "name": "Scheduled Call Agent",
                        "phoneNumber": from_number,
                        "systemPrompt": scheduled_call.get("prompt") or "You are a helpful AI assistant.",
                        "greeting": scheduled_call.get("introduction") or "Hello! I am calling regarding your scheduled appointment.",
                        "inferenceModel": "gpt-4o-mini",
                        "ttsVoice": "alloy",
                        "active": True
                    }
                    # Merge specific AI config if present
                    if scheduled_call.get("ai_config"):
                        self.agent_config.update(scheduled_call.get("ai_config"))
                        
                    logger.info(f"✅ Loaded virtual agent config from Schedule {scheduled_call_id}")
                    logger.info(f"   Greeting: '{self.agent_config.get('greeting')}'")
            except Exception as e:
                logger.error(f"❌ Error loading scheduled call config: {e}", exc_info=True)

        # Load agent config by phone number if not already provided (Priority 2)
        # For outbound calls, use AgentPhoneNumber; for inbound, use to_number
        phone_number_to_use = agent_phone_number if agent_phone_number else to_number
        
        logger.info(f"🔍 Loading agent config for phone number: {phone_number_to_use} (agent_phone_number: {agent_phone_number}, to_number: {to_number})")
        
        if not self.agent_config and phone_number_to_use:
            try:
                from databases.mongodb_agent_store import MongoDBAgentStore
                agent_store = MongoDBAgentStore()
                
                # Normalize phone number (remove +1, spaces, dashes, etc.)
                normalized_phone = phone_number_to_use.replace("+1", "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                logger.info(f"🔍 Normalized phone number for lookup: '{normalized_phone}'")
                
                # Try to find active agent with this phone number
                agents = await agent_store.list_agents(active_only=True)
                logger.info(f"🔍 Found {len(agents)} active agent(s) in database")
                
                for agent in agents:
                    agent_phone = agent.get("phoneNumber", "").replace("+1", "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                    logger.debug(f"🔍 Comparing: stored '{agent_phone}' with lookup '{normalized_phone}'")
                    if agent_phone == normalized_phone:
                        self.agent_config = agent
                        logger.info(f"✅ Loaded agent config by phone number: {agent.get('name')} (STT: {agent.get('sttModel')}, TTS: {agent.get('ttsModel')}, LLM: {agent.get('inferenceModel')})")
                        logger.info(f"   Agent greeting: '{agent.get('greeting', 'No greeting set')[:50]}...'")
                        break
                
                if not self.agent_config:
                    logger.error(f"❌ No active agent found for phone number {phone_number_to_use} (normalized: {normalized_phone})")
                    logger.error(f"   Available agents: {[a.get('name') + ' (' + a.get('phoneNumber', 'no phone') + ')' for a in agents]}")
            except Exception as e:
                logger.error(f"❌ Error loading agent config by phone number: {e}", exc_info=True)
        
        # Check for custom context for outbound calls
        # First, try to get it from stream parameters (preferred method)
        custom_context_param = custom_params.get('CustomContext')
        if custom_context_param and is_outbound and self.agent_config:
            try:
                import base64
                custom_context = base64.b64decode(custom_context_param.encode('utf-8')).decode('utf-8')
                logger.info(f"✅ Found custom context in stream parameters for outbound call")
                # Override system prompt with custom context
                self.agent_config = self.agent_config.copy()
                self.agent_config["systemPrompt"] = custom_context
                logger.info(f"🔄 Using custom context instead of agent's default system prompt")
            except Exception as e:
                logger.warning(f"Error decoding custom context from stream parameters: {e}")
        
        # Fallback: Check if custom context was stored for this outbound call (legacy method)
        if is_outbound and self.agent_config and from_number and to_number and not custom_context_param:
            try:
                from databases.mongodb_phone_store import normalize_phone_number
                # Check if custom context was stored for this outbound call
                # Access via twilio_phone_tool instance
                from tools import TwilioPhoneTool
                # Get the instance - we'll need to access it differently
                # For now, check if we can get it from the conversation_tool or import it
                try:
                    import api_general
                    if hasattr(api_general, 'twilio_phone_tool'):
                        twilio_tool = api_general.twilio_phone_tool
                        if hasattr(twilio_tool, 'outbound_call_contexts'):
                            normalized_from = normalize_phone_number(from_number)
                            normalized_to = normalize_phone_number(to_number)
                            context_key = f"{normalized_from}_{normalized_to}"
                            stored_context = twilio_tool.outbound_call_contexts.get(context_key)
                            if stored_context:
                                custom_context = stored_context.get("context")
                                logger.info(f"✅ Found custom context for outbound call in stream (legacy method): {context_key}")
                                # Override system prompt with custom context
                                self.agent_config = self.agent_config.copy()
                                self.agent_config["systemPrompt"] = custom_context
                                # Clean up stored context
                                del twilio_tool.outbound_call_contexts[context_key]
                                logger.info(f"🧹 Cleaned up stored context for {context_key}")
                except Exception as e:
                    logger.debug(f"Could not check for custom context: {e}")
            except Exception as e:
                logger.debug(f"Error checking for custom context: {e}")
        
        # If no agent config found, send error message and close stream
        if not self.agent_config:
            logger.error(f"Call {self.call_sid} rejected: Number {to_number} not found in agents collection")
            error_message = "Sorry, this number does not exist. Please check the number and try again. Goodbye."
            try:
                # Use default TTS config for error message (agent_config is None)
                # Send error message via TTS using defaults
                await self._synthesize_and_stream_tts(error_message)
                # Close the stream after message plays
                await asyncio.sleep(2)  # Give time for message to play
                await self.websocket.close()
                logger.info(f"Stream closed for unregistered number: {to_number}")
            except Exception as e:
                logger.error(f"Error sending rejection message: {e}", exc_info=True)
                # Close stream even if TTS fails
                try:
                    await self.websocket.close()
                except:
                    pass
            return
        
        # Use agent config if available
        if self.agent_config:
            logger.info(f"✅ Using agent config: {self.agent_config.get('name')} (STT: {self.agent_config.get('sttModel')}, TTS: {self.agent_config.get('ttsModel')}, LLM: {self.agent_config.get('inferenceModel')})")

        # Create a session for the call
        session_info = self.conversation_tool.create_session(
            customer_id=f"phone_{from_number}",
            persona=None
        )
        # Set system prompt in session data if agent config has one
        if self.agent_config and self.agent_config.get("systemPrompt"):
            session_info["systemPrompt"] = self.agent_config.get("systemPrompt")
        
        self.session_id = session_info.get("session_id")
        self.session_data = session_info
        
        # Register this handler in the global registry for hangup functionality
        # Import here to avoid circular dependency
        try:
            import api_general
            if hasattr(api_general, 'active_stream_handlers'):
                api_general.active_stream_handlers[self.call_sid] = self
                logger.info(f"✅ Registered stream handler for call {self.call_sid}")
        except Exception as e:
            logger.warning(f"Could not register stream handler in global registry: {e}")

    def _process_media_event(self, media_data: Dict):
        """Processes incoming 'media' events using VAD. Supports interrupt detection."""
        payload = base64.b64decode(media_data['payload'])
        
        # VAD expects 160-byte chunks for 8kHz, 20ms frames
        if len(payload) != VAD_FRAME_BYTES:
            logger.warning(f"Received unexpected payload size: {len(payload)}. Expected {VAD_FRAME_BYTES}")
            return

        is_speech = self.vad.is_speech(payload, VAD_SAMPLE_RATE)
        
        # CRITICAL: If AI is speaking, block ALL audio processing to prevent feedback loop
        # Exception: If interrupt is detected, allow capturing interrupt speech (but don't process until TTS stops)
        if self.ai_is_speaking and not self.interrupt_detected:
            # Check if this could be an interrupt (user speaking while AI is talking)
            if is_speech:
                # Check if grace period has passed (prevents AI from hearing its own voice)
                if self.ai_speech_start_time:
                    elapsed_ms = (time.time() - self.ai_speech_start_time) * 1000
                    if elapsed_ms < self.INTERRUPT_GRACE_PERIOD_MS:
                        # Still in grace period - completely ignore (definitely AI feedback)
                        return
                
                # Grace period passed - potential interrupt, start tracking
                if self.interrupt_speech_frames == 0:
                    logger.info("🔍 Potential interrupt detected, validating...")
                
                self.interrupt_speech_frames += 1
                
                # Only treat as real interrupt if speech is sustained (filters out brief AI feedback)
                if self.interrupt_speech_frames >= self.MIN_INTERRUPT_FRAMES:
                    # Validated interrupt - user is really speaking!
                    logger.info(f"🚨 INTERRUPT VALIDATED: {self.interrupt_speech_frames} frames of sustained speech!")
                    self.interrupt_detected = True
                    
                    # CRITICAL: Send Twilio "clear" command to INSTANTLY stop audio playback
                    # This stops the audio on Twilio's side immediately
                    async def send_clear_command():
                        try:
                            await self.websocket.send_json({
                                "event": "clear",
                                "streamSid": self.stream_sid
                            })
                            logger.info("🛑 Sent Twilio 'clear' command - AI audio stopped instantly!")
                        except Exception as e:
                            logger.warning(f"Could not send clear command: {e}")
                    asyncio.create_task(send_clear_command())
                    
                    # CRITICAL: Stop TTS streaming immediately and forcefully
                    if self.tts_streaming_task and not self.tts_streaming_task.done():
                        self.tts_streaming_task.cancel()
                        logger.info("🛑 Cancelled TTS streaming task due to interrupt.")
                    # Set ai_is_speaking to False immediately so interrupt can be processed faster
                    # This allows the interrupt speech to be captured and processed right away
                    self.ai_is_speaking = False
                    self.ai_speech_start_time = None
                    # Clear any existing speech buffer to start fresh
                    self.speech_buffer = bytearray()
                    self.speech_frames_count = 0
                    self.silence_frames_count = 0
                    # IMPORTANT: Start capturing the interrupt speech from this point
                    # Note: We discard the validation frames (they were just to confirm it's a real interrupt)
                    # We'll capture the full interrupt speech from now on
                    self.speech_buffer.extend(payload)
                    self.speech_frames_count = 1  # Start fresh count from validated interrupt
                    self.is_speaking = True
                    self.interrupt_speech_frames = 0  # Reset for next time
                    logger.info("🎤 Started capturing interrupt speech (waiting for TTS to stop)...")
                    return  # Don't process further in this frame, we've handled the interrupt
                else:
                    # Not enough frames yet - keep tracking but don't process
                    return
            else:
                # No speech detected - reset interrupt tracking
                self.interrupt_speech_frames = 0
                return  # Still block all audio while AI is speaking
        
        # Reset interrupt tracking if we're not in interrupt detection mode
        if not self.ai_is_speaking:
            self.interrupt_speech_frames = 0
        
        # Normal speech detection and processing
        # If interrupt is detected, allow capturing even if AI is still speaking (TTS is stopping)
        if is_speech:
            self.speech_buffer.extend(payload)
            self.speech_frames_count += 1
            self.silence_frames_count = 0
            if not self.is_speaking:
                if self.interrupt_detected:
                    logger.info("🎤 Capturing interrupt speech (AI stopping)...")
                else:
                    logger.info("Speech detected.")
                self.is_speaking = True
        elif self.is_speaking:  # Silence after speech
            self.silence_frames_count += 1
            if self.silence_frames_count >= self.SILENCE_THRESHOLD_FRAMES:
                # Only process if AI has stopped speaking (or if it's not an interrupt)
                if self.interrupt_detected and self.ai_is_speaking:
                    # Interrupt detected but TTS hasn't stopped yet - wait
                    logger.info("⏳ Interrupt speech captured, waiting for AI to stop...")
                    return
                
                logger.info("Silence threshold reached after speech, processing utterance.")
                self.is_speaking = False
                self.silence_frames_count = 0
                # Reset interrupt flag after processing
                was_interrupt = self.interrupt_detected
                self.interrupt_detected = False
                
                # CRITICAL: Cancel previous task before starting new one
                # This ensures queries are processed in sequence, not out of order
                if self.speech_processing_task and not self.speech_processing_task.done():
                    logger.info("⏳ Cancelling previous query before starting new one...")
                    # Cancel the previous task
                    self.speech_processing_task.cancel()
                    # Note: We can't await here since _process_media_event is not async
                    # The cancelled task will be cleaned up when _process_user_speech checks query_sequence
                
                # Increment query sequence AFTER cancelling previous task
                self.query_sequence += 1
                logger.info(f"🆕 Starting Query #{self.query_sequence}")
                self.speech_processing_task = asyncio.create_task(self._process_user_speech(was_interrupt=was_interrupt))

    async def _process_waiting_interrupt(self):
        """Process interrupt speech that was captured while waiting for TTS to stop.
        This is called when user interrupts the AI (e.g., stops a story to ask a new question).
        The interrupt speech contains the NEW question that should be answered, not the old response."""
        # CRITICAL: Don't wait - process immediately since TTS is already stopped
        # The interrupt was validated and TTS was cancelled, so we can process right away
        # This ensures the new question is answered quickly, not the old story
        logger.info("🔄 Processing interrupt - user asked a NEW question, ignoring previous response.")
        
        if not self.speech_buffer or self.speech_frames_count < 5:
            logger.info("⏭️ Interrupt speech too short, ignoring.")
            self.speech_buffer = bytearray()
            self.speech_frames_count = 0
            self.is_speaking = False
            self.interrupt_detected = False
            return
        
        logger.info(f"🔄 Processing waiting interrupt: {len(self.speech_buffer)} bytes")
        was_interrupt = self.interrupt_detected
        self.interrupt_detected = False
        # _process_user_speech already has the lock, so we can call it directly
        await self._process_user_speech(was_interrupt=True)
    
    async def _process_user_speech(self, was_interrupt: bool = False):
        """Transcribes the buffered speech, gets an AI response, and streams TTS back."""
        # Use lock to ensure only one processing happens at a time
        async with self.speech_processing_lock:
            # Capture the current query sequence at the start
            current_query_id = self.query_sequence
            
            # CRITICAL: Check if this task was cancelled before we acquired the lock
            # If query_sequence has changed, this query is outdated and should be skipped
            if current_query_id != self.query_sequence:
                logger.info(f"⏭️ Query #{current_query_id} is outdated (current: #{self.query_sequence}), skipping immediately")
                return
            
            # Get audio buffer snapshot (might be empty if already processed)
            if not self.speech_buffer or self.speech_frames_count < 5: # Ignore very short utterances
                if self.is_speaking: logger.info("Ignoring short utterance.")
                self.is_speaking = False
                return

            audio_to_process = self.speech_buffer.copy()
            self.speech_buffer = bytearray()
            self.speech_frames_count = 0
            
            if was_interrupt:
                logger.info(f"🔄 Processing INTERRUPT (Query #{current_query_id}): {len(audio_to_process)} bytes captured")
                conversation_history = self.session_data.get("conversation_history", [])
                logger.info(f"📚 Current conversation history: {len(conversation_history)} interactions")
                if conversation_history:
                    logger.info(f"   ✅ Interrupt question will use FULL conversation history for context")
                    logger.info(f"   Last interaction: User: '{conversation_history[-1].get('user_input', '')[:50]}...' | AI: '{conversation_history[-1].get('agent_response', '')[:50]}...'")
                else:
                    logger.info("   ⚠️ No previous interactions - this is the first question")
                logger.info("🛑 AI stopped answering previous question. 👂 Processing NEW interrupt question...")
            else:
                logger.info(f"Processing Query #{current_query_id}: {len(audio_to_process)} bytes of speech.")
                logger.info(f"📚 Current conversation history: {len(self.session_data.get('conversation_history', []))} interactions")

            try:
                wav_audio_data = convert_mulaw_to_wav_bytes(audio_to_process)
                
                # Use agent config for STT if available
                stt_model = self.agent_config.get("sttModel") if self.agent_config else None
                stt_result = await self.speech_tool.transcribe(wav_audio_data, "wav", model=stt_model)
                user_text = stt_result.get("text", "").strip()

                if not user_text:
                    logger.info("STT result is empty, skipping AI response.")
                    return
                
                # CRITICAL: Verify this is still the current query before proceeding
                # If query_sequence changed, this query is outdated and should be skipped
                if current_query_id != self.query_sequence:
                    logger.info(f"⏭️ Skipping outdated query #{current_query_id} after STT (current: #{self.query_sequence})")
                    return
                
                if was_interrupt:
                    logger.info(f"🔄 Interrupt transcription (Query #{current_query_id}): '{user_text}'")
                else:
                    logger.info(f"User said (Query #{current_query_id}): '{user_text}'")
                
                # Store user transcript in MongoDB
                try:
                    from databases.mongodb_call_store import MongoDBCallStore
                    call_store = MongoDBCallStore()
                    await call_store.update_call_transcript(
                        call_sid=self.call_sid,
                        role="user",
                        text=user_text
                    )
                except Exception as e:
                    logger.warning(f"Could not store user transcript: {e}")
                
                # Get the latest session_data right before generating response
                # This ensures we have the most up-to-date conversation history
                # CRITICAL: Log conversation history to verify it's being maintained
                conversation_history = self.session_data.get("conversation_history", [])
                logger.info(f"📚 Conversation history before Query #{current_query_id}: {len(conversation_history)} interactions")
                if conversation_history:
                    logger.info(f"   Last interaction: User: '{conversation_history[-1].get('user_input', '')[:50]}...' | AI: '{conversation_history[-1].get('agent_response', '')[:50]}...'")
                else:
                    logger.info("   No previous interactions (this is the first query)")
                
                # Use agent config for LLM if available
                llm_model = self.agent_config.get("inferenceModel") if self.agent_config else None
                temperature = self.agent_config.get("temperature") if self.agent_config else None
                max_tokens = self.agent_config.get("maxTokens") if self.agent_config else None
                
                # CRITICAL: Pass the current session_data which contains the full conversation history
                # The conversation_tool.generate_response will use this history to provide context
                # For interrupts, this ensures the AI answers the NEW question using conversation history
                if was_interrupt:
                    logger.info(f"🔄 Generating response for INTERRUPT question using conversation history...")
                    logger.info(f"   Question: '{user_text[:100]}...'")
                    logger.info(f"   History: {len(conversation_history)} previous interactions will be used for context")
                
                ai_response = await self.conversation_tool.generate_response(
                    self.session_data, user_text, None,
                    model=llm_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                response_text = ai_response.get("response", "I'm sorry, I'm having trouble with that.")
                
                # CRITICAL: Verify this is still the current query before updating session
                # If query_sequence changed, this query is outdated and should be skipped
                if current_query_id != self.query_sequence:
                    logger.info(f"⏭️ Skipping outdated query #{current_query_id} after AI response (current: #{self.query_sequence})")
                    return
                
                # CRITICAL: Update session_data with the latest conversation state
                # This ensures the next query has access to the full conversation history including this interaction
                updated_session_data = ai_response.get("session_data")
                if updated_session_data:
                    # Verify the conversation history was updated
                    old_history_count = len(self.session_data.get("conversation_history", []))
                    self.session_data = updated_session_data
                    new_history_count = len(self.session_data.get("conversation_history", []))
                    logger.info(f"✅ Updated session_data (Query #{current_query_id}): {old_history_count} -> {new_history_count} interactions")
                    
                    # Log the updated conversation history to verify it includes this interaction
                    if new_history_count > old_history_count:
                        logger.info(f"   ✅ New interaction added to history: User: '{user_text[:50]}...' | AI: '{response_text[:50]}...'")
                    else:
                        logger.warning(f"   ⚠️ Conversation history count did not increase (expected {old_history_count + 1}, got {new_history_count})")
                else:
                    logger.error(f"❌ No updated session_data returned from AI response (Query #{current_query_id})")
                
                if was_interrupt:
                    logger.info(f"💬 AI responding to INTERRUPT question (Query #{current_query_id}): '{response_text[:70]}...'")
                    logger.info(f"   ✅ Response generated using conversation history - answers NEW question, not previous story")
                else:
                    logger.info(f"AI response (Query #{current_query_id}): '{response_text[:70]}...'")
                
                # Store AI transcript in MongoDB
                try:
                    from databases.mongodb_call_store import MongoDBCallStore
                    call_store = MongoDBCallStore()
                    await call_store.update_call_transcript(
                        call_sid=self.call_sid,
                        role="assistant",
                        text=response_text
                    )
                except Exception as e:
                    logger.warning(f"Could not store AI transcript: {e}")
                
                # CRITICAL: Final check before starting TTS
                # If query_sequence changed, this query is outdated and should be skipped
                if current_query_id != self.query_sequence:
                    logger.info(f"⏭️ Skipping outdated query #{current_query_id} before TTS (current: #{self.query_sequence})")
                    return
                
                # Store TTS task so it can be cancelled if interrupted
                self.tts_streaming_task = asyncio.create_task(self._synthesize_and_stream_tts(response_text))
                try:
                    await self.tts_streaming_task
                except asyncio.CancelledError:
                    logger.info("🛑 TTS task was cancelled (interrupt handled).")
            except asyncio.CancelledError:
                logger.info(f"🛑 Speech processing task #{current_query_id} was cancelled.")
                raise
            except Exception as e:
                logger.error(f"Error processing user speech (Query #{current_query_id}): {e}", exc_info=True)

    async def _send_greeting(self):
        """Generates and streams a greeting message to the caller. For outbound calls, AI drives the conversation."""
        try:
            # For outbound calls, send greeting immediately (AI drives the conversation)
            # For inbound calls, wait a brief moment for call to fully connect
            if not self.is_outbound_call:
                await asyncio.sleep(0.5)  # Small delay for inbound calls
            
            # Check if agent_config is available
            if not self.agent_config:
                logger.error(f"❌ Cannot send greeting: agent_config is None for call {self.call_sid}")
                return
            
            # For outbound calls, AI should drive the conversation
            # Use agent's greeting if available, otherwise default
            if self.is_outbound_call:
                # For outbound calls, use greeting or a proactive message
                greeting_text = self.agent_config.get("greeting", "Hello! This is an automated call. How can I help you today?")
                logger.info(f"📢 Sending OUTBOUND call greeting for call {self.call_sid}: '{greeting_text}'")
                logger.info(f"   🚀 AI will drive this conversation (outbound call - AI speaks first)")
            else:
                # For inbound calls, use standard greeting
                greeting_text = self.agent_config.get("greeting", "Hello! How can I help you today?")
                logger.info(f"📢 Sending INBOUND call greeting for call {self.call_sid}: '{greeting_text}'")
                
            # Store greeting in MongoDB transcript
            try:
                from databases.mongodb_call_store import MongoDBCallStore
                call_store = MongoDBCallStore()
                await call_store.update_call_transcript(
                    call_sid=self.call_sid,
                    role="assistant",
                    text=greeting_text
                )
                logger.info(f"✅ Stored greeting in transcript for call {self.call_sid}")
            except Exception as e:
                logger.warning(f"Could not store greeting transcript: {e}")
            
            # Store TTS task for potential cancellation
            logger.info(f"🎤 Starting TTS for greeting: '{greeting_text[:50]}...'")
            self.tts_streaming_task = asyncio.create_task(self._synthesize_and_stream_tts(greeting_text))
            await self.tts_streaming_task
            logger.info(f"✅ Greeting TTS completed for call {self.call_sid}")
        except Exception as e:
            logger.error(f"❌ Error sending greeting for call {self.call_sid}: {e}", exc_info=True)

    async def _synthesize_and_stream_tts(self, text: str):
        """Synthesizes text to speech and streams it back to Twilio using fast PCM conversion.
        Supports interruption - will stop streaming if user interrupts."""
        logger.info(f"Streaming TTS for text: '{text[:50]}...'")
        
        # Set flag to prevent processing incoming audio (feedback loop prevention)
        self.ai_is_speaking = True
        self.ai_speech_start_time = time.time()  # Record when AI started speaking (for grace period)
        logger.info("🔇 AI started speaking, muting user audio input (grace period active).")
        
        # Get agent config for TTS if available
        tts_voice = self.agent_config.get("ttsVoice", "alloy") if self.agent_config else "alloy"
        tts_model = self.agent_config.get("ttsModel") if self.agent_config else None
        
        try:
            sentences = self.tts_tool._split_into_sentences(text)
            for sentence in sentences:
                # CRITICAL: Check for interrupt before processing each sentence
                # If interrupt detected, stop immediately and don't process any more sentences
                if self.interrupt_detected:
                    logger.info("🛑 TTS interrupted by user, stopping stream immediately.")
                    self.ai_is_speaking = False
                    self.ai_speech_start_time = None
                    # Don't send any more audio - user wants to ask a new question
                    return
                
                if not sentence.strip():
                    continue
                
                # Get TTS in PCM format for fast conversion (no ffmpeg needed!)
                # Use agent config for TTS voice and model
                tts_result = await self._synthesize_pcm(sentence, voice=tts_voice, model=tts_model)
                
                # Check again after TTS generation (user might have interrupted during generation)
                if self.interrupt_detected:
                    logger.info("🛑 TTS interrupted after generation, stopping stream.")
                    self.ai_is_speaking = False
                    return
                
                if tts_result.get("success"):
                    # CRITICAL: Check for interrupt BEFORE sending audio chunk
                    if self.interrupt_detected:
                        logger.info("🛑 Interrupt detected before sending audio chunk, stopping immediately.")
                        self.ai_is_speaking = False
                        return
                    
                    pcm_bytes = tts_result["audio_bytes"]
                    # CRITICAL: Check for interrupt BEFORE conversion (saves processing time)
                    if self.interrupt_detected:
                        logger.info("🛑 Interrupt detected before audio conversion, stopping immediately.")
                        self.ai_is_speaking = False
                        return
                    
                    # Fast conversion: PCM -> mu-law using only Python audioop (no ffmpeg)
                    mulaw_bytes = convert_pcm_to_mulaw(pcm_bytes, input_rate=24000, input_width=2)
                    if mulaw_bytes:
                        # CRITICAL: Check AGAIN right before sending (interrupt might have happened during conversion)
                        # This is the LAST chance to stop before audio is sent to user
                        if self.interrupt_detected:
                            logger.info("🛑 Interrupt detected right before sending, aborting audio chunk - STOPPING IMMEDIATELY.")
                            self.ai_is_speaking = False
                            return
                        
                        payload = base64.b64encode(mulaw_bytes).decode('utf-8')
                        # CRITICAL: Final check right before sending to websocket
                        # If interrupt happened, don't send this chunk - user wants to ask new question
                        if self.interrupt_detected:
                            logger.info("🛑 Interrupt detected during payload encoding, stopping - NO MORE AUDIO.")
                            self.ai_is_speaking = False
                            return
                        
                        await self.websocket.send_json({
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": payload}
                        })
                else:
                    logger.error(f"TTS failed for sentence: {sentence}")

            # Only send end mark if we weren't interrupted
            if not self.interrupt_detected:
                # Send mark to signal end of speech (will trigger ai_is_speaking = False in mark handler)
                await self.websocket.send_json({
                    "event": "mark",
                    "streamSid": self.stream_sid,
                    "mark": {"name": "end_of_ai_speech"}
                })
                logger.info("Finished streaming AI response.")
            else:
                # CRITICAL: If interrupted, stop immediately and process the new question
                # Don't send end mark - we're stopping mid-response (e.g., story was interrupted)
                self.ai_is_speaking = False
                self.ai_speech_start_time = None
                self.interrupt_speech_frames = 0
                logger.info("✅ TTS stream interrupted - stopping story, ready for new question.")
                # CRITICAL: Process interrupt speech immediately - user asked a new question
                # Don't wait, process it right away
                if self.is_speaking and self.speech_buffer:
                    logger.info("🔄 TTS stopped, processing interrupt question immediately...")
                    asyncio.create_task(self._process_waiting_interrupt())
                else:
                    logger.warning("⚠️ Interrupt detected but no speech buffer available")
        except asyncio.CancelledError:
            logger.info("🛑 TTS streaming task was cancelled (interrupt) - stopping story immediately.")
            self.ai_is_speaking = False
            self.ai_speech_start_time = None
            self.interrupt_speech_frames = 0
            # CRITICAL: Process interrupt speech immediately - user asked a new question
            if self.is_speaking and self.speech_buffer:
                logger.info("🔄 TTS cancelled, processing interrupt question immediately...")
                asyncio.create_task(self._process_waiting_interrupt())
            else:
                logger.warning("⚠️ TTS cancelled but no interrupt speech buffer available")
            raise
        except Exception as e:
            logger.error(f"Error in TTS streaming: {e}", exc_info=True)
            # Make sure to re-enable listening even if TTS fails
            self.ai_is_speaking = False
            self.ai_speech_start_time = None
            self.interrupt_speech_frames = 0
            logger.info("✅ AI speech error, re-enabling user audio.")
    
    async def _synthesize_pcm(self, text: str, voice: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Generate TTS in PCM format for fast streaming (no conversion overhead)."""
        try:
            # Use provided voice/model or fall back to agent config or defaults
            tts_voice = voice or (self.agent_config.get("ttsVoice", "alloy") if self.agent_config else "alloy")
            tts_model = model or (self.agent_config.get("ttsModel") if self.agent_config else self.tts_tool.model)
            
            response = self.tts_tool.client.audio.speech.create(
                model=tts_model,
                voice=tts_voice,
                input=text,
                response_format="pcm"  # Raw PCM - fastest, no decoding needed
            )
            return {
                "success": True,
                "audio_bytes": response.content
            }
        except Exception as e:
            logger.error(f"PCM TTS synthesis failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def hangup_call(self, reason: str = "Call ended by system"):
        """Hang up the call by sending a clear command to Twilio."""
        try:
            logger.info(f"📞 Hanging up call {self.call_sid}: {reason}")
            
            # Unregister from global registry
            try:
                import api_general
                if hasattr(api_general, 'active_stream_handlers') and self.call_sid in api_general.active_stream_handlers:
                    del api_general.active_stream_handlers[self.call_sid]
                    logger.info(f"✅ Unregistered stream handler for call {self.call_sid}")
            except Exception as e:
                logger.warning(f"Could not unregister stream handler: {e}")
            
            # Send clear command to Twilio to hang up the call
            try:
                await self.websocket.send_json({
                    "event": "clear",
                    "streamSid": self.stream_sid
                })
            except Exception as e:
                logger.warning(f"Could not send clear command via WebSocket: {e}")
            
            # Also try to update call status via REST API if available
            try:
                from utils.twilio_credentials import get_twilio_credentials
                twilio_creds = await get_twilio_credentials(phone_number=self.to_number, call_sid=self.call_sid)
                if twilio_creds and twilio_creds.get("account_sid") and twilio_creds.get("auth_token"):
                    from twilio.rest import Client
                    client = Client(twilio_creds["account_sid"], twilio_creds["auth_token"])
                    call = client.calls(self.call_sid).update(status="completed")
                    logger.info(f"✅ Call {self.call_sid} status updated to completed via REST API")
                    
                    # Update call status in MongoDB immediately
                    try:
                        from databases.mongodb_call_store import MongoDBCallStore
                        call_store = MongoDBCallStore()
                        await call_store.end_call(self.call_sid)
                        logger.info(f"✅ Updated call {self.call_sid} status to 'completed' in MongoDB")
                    except Exception as e:
                        logger.warning(f"Could not update call status in MongoDB: {e}")
            except Exception as e:
                logger.warning(f"Could not update call status via REST API: {e}")
            
            # Close the WebSocket connection
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            
            logger.info(f"✅ Call {self.call_sid} hung up successfully")
            return True
        except Exception as e:
            logger.error(f"Error hanging up call {self.call_sid}: {e}", exc_info=True)
            return False

    def _handle_stop_event(self, stop_data: Dict):
        """Handles the 'stop' event from Twilio stream."""
        logger.info(f"Stream stopped for call SID: {self.call_sid}. Cleaning up.")
        
        # End call in MongoDB
        try:
            from databases.mongodb_call_store import MongoDBCallStore
            call_store = MongoDBCallStore()
            asyncio.create_task(call_store.end_call(self.call_sid))
        except Exception as e:
            logger.warning(f"Could not end call record: {e}")
        
        # Clean up from global registry
        try:
            import api_general
            if hasattr(api_general, 'active_stream_handlers') and self.call_sid in api_general.active_stream_handlers:
                del api_general.active_stream_handlers[self.call_sid]
                logger.info(f"✅ Unregistered stream handler for call {self.call_sid} (stop event)")
        except Exception as e:
            logger.warning(f"Could not unregister stream handler: {e}")
        
        # Cancel any active tasks
        if self.tts_streaming_task and not self.tts_streaming_task.done():
            self.tts_streaming_task.cancel()
        if self.speech_processing_task and not self.speech_processing_task.done():
            self.speech_processing_task.cancel()
        
        logger.info(f"✅ Call {self.call_sid} cleanup completed")
