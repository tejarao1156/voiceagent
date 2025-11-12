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
        
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.speech_buffer = bytearray()
        self.is_speaking = False  # User is speaking
        self.ai_is_speaking = False  # AI is speaking (prevents feedback loop)
        self.interrupt_detected = False  # User interrupted AI
        self.tts_streaming_task = None  # Track active TTS streaming task for cancellation
        self.ai_speech_start_time = None  # Timestamp when AI started speaking (for grace period)
        self.stream_sid = None
        self.call_sid = None
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
                # Asynchronously send the greeting message
                asyncio.create_task(self._send_greeting())
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
                    # If there's waiting interrupt speech, process it now
                    if was_interrupted and self.is_speaking and self.speech_buffer:
                        logger.info("🔄 AI stopped, processing waiting interrupt speech...")
                        # Increment query sequence and cancel any existing speech processing task
                        self.query_sequence += 1
                        if self.speech_processing_task and not self.speech_processing_task.done():
                            logger.info("🛑 Cancelling previous speech processing task (interrupt received)")
                            self.speech_processing_task.cancel()
                        self.speech_processing_task = asyncio.create_task(self._process_waiting_interrupt())

    async def _handle_start_event(self, start_data: Dict):
        """Handles the 'start' event from Twilio stream."""
        self.stream_sid = start_data['streamSid']
        self.call_sid = start_data['callSid']
        from_number = start_data.get('customParameters', {}).get('From', 'Unknown')
        to_number = start_data.get('customParameters', {}).get('To', 'Unknown')
        
        logger.info(f"Stream started: call_sid={self.call_sid}, stream_sid={self.stream_sid}")
        logger.info(f"Call from: {from_number} to: {to_number}")
        
        # Load agent config by phone number if not already provided
        if not self.agent_config and to_number:
            try:
                from databases.mongodb_agent_store import MongoDBAgentStore
                agent_store = MongoDBAgentStore()
                
                # Normalize phone number (remove +1, spaces, dashes, etc.)
                normalized_phone = to_number.replace("+1", "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                
                # Try to find active agent with this phone number
                agents = await agent_store.list_agents(active_only=True)
                
                for agent in agents:
                    agent_phone = agent.get("phoneNumber", "").replace("+1", "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                    if agent_phone == normalized_phone:
                        self.agent_config = agent
                        logger.info(f"✅ Loaded agent config by phone number: {agent.get('name')} (STT: {agent.get('sttModel')}, TTS: {agent.get('ttsModel')}, LLM: {agent.get('inferenceModel')})")
                        break
                
                if not self.agent_config:
                    logger.warning(f"❌ No active agent found for phone number {to_number}")
            except Exception as e:
                logger.error(f"Error loading agent config by phone number: {e}", exc_info=True)
        
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
                    # Stop TTS streaming immediately
                    if self.tts_streaming_task and not self.tts_streaming_task.done():
                        self.tts_streaming_task.cancel()
                        logger.info("🛑 Cancelled TTS streaming task due to interrupt.")
                    
                    # IMPORTANT: Keep ai_is_speaking = True for now to block audio processing
                    # The TTS function will set it to False when it actually stops
                    # This ensures we don't process the interrupt until TTS has fully stopped
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
                # Increment query sequence and cancel any existing speech processing task
                self.query_sequence += 1
                if self.speech_processing_task and not self.speech_processing_task.done():
                    logger.info("🛑 Cancelling previous speech processing task (new query received)")
                    self.speech_processing_task.cancel()
                self.speech_processing_task = asyncio.create_task(self._process_user_speech(was_interrupt=was_interrupt))

    async def _process_waiting_interrupt(self):
        """Process interrupt speech that was captured while waiting for TTS to stop."""
        # Wait a tiny bit to ensure TTS has fully stopped
        await asyncio.sleep(0.1)
        
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
                logger.info(f"📚 Current conversation history: {len(self.session_data.get('conversation_history', []))} interactions")
                logger.info("🛑 AI stopped. 👂 Listening to interrupt...")
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
                
                # Verify this is still the current query (lock should prevent this, but double-check)
                if current_query_id != self.query_sequence:
                    logger.info(f"⏭️ Skipping outdated query #{current_query_id} after STT (current: #{self.query_sequence})")
                    return
                
                if was_interrupt:
                    logger.info(f"🔄 Interrupt transcription (Query #{current_query_id}): '{user_text}'")
                else:
                    logger.info(f"User said (Query #{current_query_id}): '{user_text}'")
                
                # Get the latest session_data right before generating response
                # This ensures we have the most up-to-date conversation history
                # Use agent config for LLM if available
                llm_model = self.agent_config.get("inferenceModel") if self.agent_config else None
                temperature = self.agent_config.get("temperature") if self.agent_config else None
                max_tokens = self.agent_config.get("maxTokens") if self.agent_config else None
                
                ai_response = await self.conversation_tool.generate_response(
                    self.session_data, user_text, None,
                    model=llm_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                response_text = ai_response.get("response", "I'm sorry, I'm having trouble with that.")
                
                # Verify this is still the current query before updating session
                if current_query_id != self.query_sequence:
                    logger.info(f"⏭️ Skipping outdated query #{current_query_id} after AI response (current: #{self.query_sequence})")
                    return
                
                # CRITICAL: Update session_data with the latest conversation state
                # This ensures interrupts have access to the full conversation history
                updated_session_data = ai_response.get("session_data")
                if updated_session_data:
                    self.session_data = updated_session_data
                    logger.info(f"✅ Updated session_data (Query #{current_query_id}): {len(self.session_data.get('conversation_history', []))} interactions")
                
                if was_interrupt:
                    logger.info(f"💬 AI responding to interrupt (Query #{current_query_id}): '{response_text[:70]}...'")
                else:
                    logger.info(f"AI response (Query #{current_query_id}): '{response_text[:70]}...'")
                
                # Final check before starting TTS
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
        """Generates and streams a greeting message to the caller."""
        # Use agent's greeting if available, otherwise default
        greeting_text = self.agent_config.get("greeting", "Hello! How can I help you today?") if self.agent_config else "Hello! How can I help you today?"
        logger.info(f"Sending greeting: '{greeting_text}'")
        # Store TTS task for potential cancellation
        self.tts_streaming_task = asyncio.create_task(self._synthesize_and_stream_tts(greeting_text))
        await self.tts_streaming_task

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
                # Check for interrupt before processing each sentence
                if self.interrupt_detected:
                    logger.info("🛑 TTS interrupted by user, stopping stream.")
                    self.ai_is_speaking = False
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
                    # Fast conversion: PCM -> mu-law using only Python audioop (no ffmpeg)
                    mulaw_bytes = convert_pcm_to_mulaw(pcm_bytes, input_rate=24000, input_width=2)
                    if mulaw_bytes:
                        # Check AGAIN right before sending (interrupt might have happened during conversion)
                        if self.interrupt_detected:
                            logger.info("🛑 Interrupt detected right before sending, aborting audio chunk.")
                            self.ai_is_speaking = False
                            return
                        
                        payload = base64.b64encode(mulaw_bytes).decode('utf-8')
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
                # If interrupted, manually clear the flag
                self.ai_is_speaking = False
                self.ai_speech_start_time = None
                self.interrupt_speech_frames = 0
                logger.info("✅ TTS stream interrupted, ready for user input.")
                # Trigger processing of waiting interrupt speech
                if self.is_speaking and self.speech_buffer:
                    logger.info("🔄 TTS stopped, processing waiting interrupt speech...")
                    asyncio.create_task(self._process_waiting_interrupt())
        except asyncio.CancelledError:
            logger.info("🛑 TTS streaming task was cancelled (interrupt).")
            self.ai_is_speaking = False
            self.ai_speech_start_time = None
            self.interrupt_speech_frames = 0
            # Trigger processing of waiting interrupt speech
            if self.is_speaking and self.speech_buffer:
                logger.info("🔄 TTS cancelled, processing waiting interrupt speech...")
                asyncio.create_task(self._process_waiting_interrupt())
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
                from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
                if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
                    from twilio.rest import Client
                    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    call = client.calls(self.call_sid).update(status="completed")
                    logger.info(f"✅ Call {self.call_sid} status updated to completed via REST API")
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
