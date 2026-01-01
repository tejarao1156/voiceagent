import asyncio
import json
import base64
import logging
import time
import audioop
from fastapi import WebSocket
from typing import Dict, Any, Optional, List

import webrtcvad

from tools import SpeechToTextTool, ConversationalResponseTool, TextToSpeechTool
from tools.phone.audio_utils import convert_pcm_to_mulaw, convert_mulaw_to_wav_bytes, normalize_audio, apply_noise_gate
from tools.provider_factory import get_stt_tool, get_tts_tool, is_elevenlabs_tts, is_deepgram_stt, is_deepgram_tts
from tools.language_config import is_language_supported, get_language_names
from conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

# VAD configuration
VAD_AGGRESSIVENESS = 3
VAD_SAMPLE_RATE = 8000  # Twilio media stream is 8kHz mu-law
VAD_FRAME_DURATION_MS = 20
VAD_FRAME_BYTES = (VAD_SAMPLE_RATE * VAD_FRAME_DURATION_MS // 1000)

# Audio quality thresholds for human-like conversation
# TUNED for quiet speakers per ElevenLabs VAD best practices:
# - Lower RMS threshold = more sensitive to soft voices
# - Fewer frames = faster speech detection
MIN_RMS_THRESHOLD = 250  # Lower threshold for quiet speakers (was 500)
MIN_SPEECH_DURATION_FRAMES = 6  # 6 frames * 20ms = 120ms minimum speech (was 8)

# INTERRUPT-SPECIFIC THRESHOLDS (higher than normal speech to reduce false positives)
# These require stronger signals to trigger interrupts during AI playback
# This prevents background noise, AI echo, and quiet sounds from stopping the AI
MIN_INTERRUPT_RMS_THRESHOLD = 400  # Base RMS threshold (may be raised by noise floor)

# NOISE FLOOR CALIBRATION - Measures ambient noise to set dynamic thresholds
# Calibrates during first 500ms after AI starts speaking
NOISE_CALIBRATION_FRAMES = 25  # 25 frames * 20ms = 500ms calibration period
NOISE_MARGIN = 300  # RMS margin above noise floor for interrupt detection

# PRIMARY SPEAKER DETECTION - Filters out background speech (guy talking in back)
# Caller's voice is louder than background because they hold phone to mouth
PRIMARY_SPEAKER_MULTIPLIER = 2.0  # Voice must be 2x louder than noise floor
MAX_INTERRUPT_RMS_VARIANCE = 30000  # Max variance - increased for PSTN call quality (was 15000)
MAX_DYNAMIC_THRESHOLD = 800  # Cap max threshold to prevent runaway from AI echo in calibration

# Noise phrase filtering - common STT artifacts that should be ignored
NOISE_PHRASES = {
    "you", "uh", "um", "hmm", "ah", "oh", "huh", "eh", "mm", "mhm",
    ".", "..", "...", " ", "", "the", "a", "i", "it", "is", "to"
}
# Single character patterns are also noise
MIN_TRANSCRIPT_LENGTH = 3  # Minimum characters for valid transcript

# Valid short responses that should NOT be filtered even if < MIN_TRANSCRIPT_LENGTH
VALID_SHORT_RESPONSES = {"ok", "no", "hi", "go", "ya", "ye", "by", "bye"}

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
        
        # Human-like conversation tuning parameters
        # TUNED to reduce false interrupt triggers while maintaining responsive barge-in
        self.SILENCE_THRESHOLD_FRAMES = 150  # 150 frames * 20ms = 3s - gives user time to pause
        self.INTERRUPT_GRACE_PERIOD_MS = 300  # Wait 300ms after AI starts before allowing interrupts (prevents AI echo)
        self.MIN_INTERRUPT_FRAMES = 7  # Require 7 frames (140ms) of sustained speech for valid interrupt (was 10)
        
        # Audio quality validation
        self.rms_buffer: List[int] = []  # Track RMS values for average calculation
        self.interrupt_rms_buffer: List[int] = []  # Track RMS values during interrupt validation
        self.greeting_complete = False  # Block speech processing until greeting finishes
        self.call_settling_complete = False  # Block speech until call has settled
        self.last_interrupt_time = 0.0  # Track last interrupt time for debouncing
        self.INTERRUPT_DEBOUNCE_MS = 200  # 200ms between interrupts - allows quick re-interrupts (was 300ms)
        
        # NOISE FLOOR CALIBRATION - Measures ambient noise to set dynamic thresholds
        self.noise_floor: float = 0.0  # Calibrated ambient noise level (RMS)
        self.noise_calibration_buffer: List[int] = []  # RMS samples during calibration
        self.noise_calibration_complete: bool = False  # Flag for calibration state
        self.dynamic_interrupt_threshold: int = MIN_INTERRUPT_RMS_THRESHOLD  # Dynamic threshold based on noise
        
        self.speech_processing_lock = asyncio.Lock()  # Prevent concurrent speech processing
        self.speech_processing_task = None  # Track active speech processing task for cancellation
        self.query_sequence = 0  # Track query sequence to ensure we process the most recent
        
        # Speculative STT: Process audio in background while user is speaking
        self.speculative_stt_task = None  # Background STT task
        self.pending_transcription = ""  # Latest partial transcription result
        self.last_stt_time = 0.0  # Last time we sent audio to STT (for debouncing)
        self.SPECULATIVE_STT_INTERVAL_MS = 750  # Send audio to STT every 750ms during speech
        self.speculative_audio_buffer = bytearray()  # Audio buffer for speculative STT
        
        # Stop words that trigger auto-hangup after AI speaks them
        self.CALL_END_PHRASES = [
            "goodbye", "bye-bye", "bye bye", "good bye", "bye.",
            "take care", "have a great day", "have a good day",
            "talk to you later", "speak to you later", "have a nice day",
            "thanks for calling", "thank you for calling"
        ]
        
        # === EDGE CASE HANDLING: Silence and Duration Timeouts ===
        # Inactivity timeout: hang up if user doesn't speak for too long after greeting
        self.INACTIVITY_TIMEOUT_SECONDS = 30  # Hangup after 30s of no user speech
        self.PROMPT_AFTER_SILENCE_SECONDS = 8  # Prompt "Are you still there?" after 8s silence
        self.last_user_speech_time: Optional[float] = None  # Track when user last spoke
        self.silence_prompt_sent = False  # Track if we already sent silence prompt
        self.inactivity_check_task: Optional[asyncio.Task] = None  # Background task for inactivity check
        
        # Max call duration: prevent calls from running forever
        self.MAX_CALL_DURATION_SECONDS = 300  # 5 minutes max call duration
        self.call_start_time: Optional[float] = None  # Track when call started
    
    def _should_end_call(self, text: str) -> bool:
        """Check if text contains farewell phrases indicating call should end."""
        text_lower = text.lower()
        for phrase in self.CALL_END_PHRASES:
            if phrase in text_lower:
                return True
        return False

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
                await self._handle_stop_event(data['stop'])
                break
            elif event == 'mark':
                mark_name = data['mark']['name']
                logger.info(f"Received mark event: {mark_name}")
                # When AI finishes speaking a sentence, re-enable user audio processing
                # NOTE: For multi-sentence responses, this fires after EACH sentence
                if mark_name == "end_of_ai_speech":
                    was_interrupted = self.interrupt_detected
                    self.ai_is_speaking = False
                    self.ai_speech_start_time = None
                    # DON'T reset interrupt_speech_frames here!
                    # Interrupt tracking must persist across sentence boundaries
                    # Otherwise user can't interrupt during long multi-sentence responses
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
        
        # =====================================================================
        # CODE REUSE: Use agent_config from webhook (same flow for incoming/outgoing)
        # =====================================================================
        # PRIORITY 0: Check if agent_config was passed from webhook
        # This reuses the already-loaded config, avoiding double-loading and normalization issues
        agent_config_param = custom_params.get('AgentConfig')
        if not self.agent_config and agent_config_param:
            try:
                import json
                decoded_config = base64.b64decode(agent_config_param.encode('utf-8')).decode('utf-8')
                self.agent_config = json.loads(decoded_config)
                logger.info(f"✅ Using agent_config from webhook (reused code path): {self.agent_config.get('name')}")
                logger.info(f"   Greeting: '{self.agent_config.get('greeting', 'No greeting')[:50]}...'")
            except Exception as e:
                logger.warning(f"Could not decode agent_config from webhook: {e}")
        
        # Check for Scheduled Call ID (Priority 1)
        scheduled_call_id = custom_params.get('ScheduledCallId')
        if not self.agent_config and scheduled_call_id:
            try:
                logger.info(f"🗓️ Loading config from Scheduled Call ID: {scheduled_call_id}")
                from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
                scheduled_store = MongoDBScheduledCallStore()
                scheduled_call = await scheduled_store.get_scheduled_call(scheduled_call_id)
                
                if scheduled_call:
                    # Construct virtual agent config with all AI model defaults
                    self.agent_config = {
                        "name": "Scheduled Call Agent",
                        "phoneNumber": from_number,
                        "systemPrompt": scheduled_call.get("prompt") or "You are a helpful AI assistant.",
                        "greeting": scheduled_call.get("introduction") or "Hello! I am calling regarding your scheduled appointment.",
                        # Default AI model configuration (will be overridden by ai_config if present)
                        "sttModel": "whisper-1",
                        "inferenceModel": "gpt-4o-mini",
                        "ttsModel": "tts-1",
                        "ttsVoice": "alloy",
                        "active": True
                    }
                    # Merge specific AI config if present (overrides defaults)
                    if scheduled_call.get("ai_config"):
                        self.agent_config.update(scheduled_call.get("ai_config"))
                        logger.info(f"   AI Config: STT={self.agent_config.get('sttModel')}, LLM={self.agent_config.get('inferenceModel')}, TTS={self.agent_config.get('ttsModel')}, Voice={self.agent_config.get('ttsVoice')}")
                        
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
        # CRITICAL: Use snake_case "system_prompt" to match what conversation_manager.py expects
        if self.agent_config and self.agent_config.get("systemPrompt"):
            session_info["system_prompt"] = self.agent_config.get("systemPrompt")
        
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

    def _calculate_rms(self, audio_bytes: bytes) -> int:
        """Calculate RMS (Root Mean Square) energy of audio chunk.
        Higher RMS = louder audio. Used to filter out background noise."""
        try:
            # For mu-law encoded audio at 8kHz, each sample is 1 byte
            # Convert to linear PCM first for accurate RMS
            linear_pcm = audioop.ulaw2lin(audio_bytes, 2)  # 2 bytes per sample output
            return audioop.rms(linear_pcm, 2)
        except Exception as e:
            logger.warning(f"RMS calculation error: {e}")
            return 0
    
    def _get_average_rms(self) -> float:
        """Get average RMS from the buffer."""
        if not self.rms_buffer:
            return 0.0
        return sum(self.rms_buffer) / len(self.rms_buffer)
    
    def _is_valid_transcript(self, text: str) -> bool:
        """Validate that transcript is meaningful speech, not noise.
        Returns False for single chars, noise words, and very short text."""
        if not text:
            return False
        
        text_clean = text.strip().lower()
        
        # Allow valid short responses even if < MIN_TRANSCRIPT_LENGTH
        if text_clean in VALID_SHORT_RESPONSES:
            return True
        
        # Too short (but not in valid short responses)
        if len(text_clean) < MIN_TRANSCRIPT_LENGTH:
            logger.info(f"🔇 Rejecting short transcript: '{text}' ({len(text_clean)} chars < {MIN_TRANSCRIPT_LENGTH})")
            return False
        
        # Known noise phrases
        if text_clean in NOISE_PHRASES:
            logger.info(f"🔇 Rejecting noise phrase: '{text}'")
            return False
        
        # Single words that are likely noise
        words = text_clean.split()
        if len(words) == 1 and text_clean in NOISE_PHRASES:
            logger.info(f"🔇 Rejecting single noise word: '{text}'")
            return False
        
        return True
    
    def _process_media_event(self, media_data: Dict):
        """Processes incoming 'media' events using VAD. Supports interrupt detection.
        Includes audio energy validation and greeting lock for human-like conversation."""
        payload = base64.b64decode(media_data['payload'])
        
        # VAD expects 160-byte chunks for 8kHz, 20ms frames
        if len(payload) != VAD_FRAME_BYTES:
            logger.warning(f"Received unexpected payload size: {len(payload)}. Expected {VAD_FRAME_BYTES}")
            return
        
        # PHASE 1: Call settling check - ignore all audio until call has settled
        if not self.call_settling_complete:
            return
        
        # PHASE 2: Greeting lock - block all speech processing until greeting completes
        if not self.greeting_complete:
            return
        
        # PHASE 3: Calculate audio energy (RMS) to filter out low-volume noise
        rms = self._calculate_rms(payload)
        
        # Only consider as potential speech if RMS exceeds threshold
        is_speech_by_vad = self.vad.is_speech(payload, VAD_SAMPLE_RATE)
        is_speech = is_speech_by_vad and rms >= MIN_RMS_THRESHOLD
        
        # Log when VAD detects speech but RMS is too low (filtered noise)
        if is_speech_by_vad and not is_speech:
            logger.debug(f"🔇 VAD detected speech but RMS too low ({rms} < {MIN_RMS_THRESHOLD}), filtering as noise")
        
        # CRITICAL: If AI is speaking, block ALL audio processing to prevent feedback loop
        # Exception: If interrupt is detected, allow capturing interrupt speech (but don't process until TTS stops)
        if self.ai_is_speaking and not self.interrupt_detected:
            # === NOISE FLOOR CALIBRATION ===
            # During first 500ms (25 frames) after AI starts, measure ambient noise
            if not self.noise_calibration_complete:
                self.noise_calibration_buffer.append(rms)
                if len(self.noise_calibration_buffer) >= NOISE_CALIBRATION_FRAMES:
                    # Calculate noise floor as average RMS during calibration
                    self.noise_floor = sum(self.noise_calibration_buffer) / len(self.noise_calibration_buffer)
                    
                    # Calculate dynamic threshold: max of base threshold or noise_floor + margin
                    # Also apply primary speaker multiplier (2x noise floor)
                    # BUT cap at MAX_DYNAMIC_THRESHOLD to prevent runaway from AI echo
                    threshold_from_margin = self.noise_floor + NOISE_MARGIN
                    threshold_from_multiplier = self.noise_floor * PRIMARY_SPEAKER_MULTIPLIER
                    uncapped_threshold = max(
                        MIN_INTERRUPT_RMS_THRESHOLD,
                        threshold_from_margin,
                        threshold_from_multiplier
                    )
                    self.dynamic_interrupt_threshold = int(min(uncapped_threshold, MAX_DYNAMIC_THRESHOLD))
                    
                    self.noise_calibration_complete = True
                    logger.info(f"📊 Noise floor calibrated: {self.noise_floor:.0f} RMS → threshold: {self.dynamic_interrupt_threshold} (capped at {MAX_DYNAMIC_THRESHOLD})")
                # During calibration, don't allow interrupts (still in grace period anyway)
                return
            
            # Check if this could be an interrupt (user speaking while AI is talking)
            if is_speech:
                # Check if grace period has passed (prevents AI from hearing its own voice)
                if self.ai_speech_start_time:
                    elapsed_ms = (time.time() - self.ai_speech_start_time) * 1000
                    if elapsed_ms < self.INTERRUPT_GRACE_PERIOD_MS:
                        # Still in grace period - completely ignore (definitely AI feedback)
                        return
                
                # Check interrupt debounce - prevent rapid false triggers
                time_since_last_interrupt = (time.time() - self.last_interrupt_time) * 1000
                if time_since_last_interrupt < self.INTERRUPT_DEBOUNCE_MS:
                    # Too soon after last interrupt - ignore
                    return
                
                # === PRIMARY SPEAKER DETECTION ===
                # Use dynamic threshold to filter background noise and background chatter
                if rms < self.dynamic_interrupt_threshold:
                    # Speech detected but RMS too low - likely noise, AI echo, or guy talking in background
                    if self.interrupt_speech_frames == 0:
                        logger.debug(f"🔇 Potential interrupt ignored - RMS {rms} < dynamic threshold {self.dynamic_interrupt_threshold} (noise floor: {self.noise_floor:.0f})")
                    self.interrupt_speech_frames = 0  # Reset counter since this wasn't strong enough
                    return
                
                # Dynamic threshold passed - potential interrupt from PRIMARY speaker, start tracking
                if self.interrupt_speech_frames == 0:
                    logger.info(f"🔍 Potential interrupt detected (RMS: {rms} >= threshold {self.dynamic_interrupt_threshold}), validating...")
                    self.interrupt_rms_buffer = []  # Reset RMS buffer for new potential interrupt
                
                self.interrupt_speech_frames += 1
                self.interrupt_rms_buffer.append(rms)  # Track RMS for cumulative validation
                
                # Only treat as real interrupt if speech is sustained (filters out brief noise spikes)
                if self.interrupt_speech_frames >= self.MIN_INTERRUPT_FRAMES:
                    # Calculate average RMS across all interrupt frames
                    avg_interrupt_rms = sum(self.interrupt_rms_buffer) / len(self.interrupt_rms_buffer) if self.interrupt_rms_buffer else 0
                    
                    # Final validation 1: average RMS must still be above dynamic threshold
                    if avg_interrupt_rms < self.dynamic_interrupt_threshold:
                        logger.info(f"🔇 Interrupt rejected - avg RMS {avg_interrupt_rms:.0f} < threshold {self.dynamic_interrupt_threshold}")
                        self.interrupt_speech_frames = 0
                        self.interrupt_rms_buffer = []
                        return
                    
                    # Final validation 2: Check RMS variance (background chatter has high variance)
                    if len(self.interrupt_rms_buffer) >= 3:
                        mean_rms = avg_interrupt_rms
                        variance = sum((x - mean_rms) ** 2 for x in self.interrupt_rms_buffer) / len(self.interrupt_rms_buffer)
                        if variance > MAX_INTERRUPT_RMS_VARIANCE:
                            logger.info(f"🔇 Interrupt rejected - high RMS variance {variance:.0f} > {MAX_INTERRUPT_RMS_VARIANCE} (likely background chatter)")
                            self.interrupt_speech_frames = 0
                            self.interrupt_rms_buffer = []
                            return
                    
                    # Validated interrupt - user is really speaking with sustained, consistent energy!
                    logger.info(f"🚨 INTERRUPT VALIDATED: {self.interrupt_speech_frames} frames, avg RMS: {avg_interrupt_rms:.0f}, threshold: {self.dynamic_interrupt_threshold}!")
                    self.interrupt_detected = True
                    self.last_interrupt_time = time.time()  # Record for debouncing
                    
                    # CRITICAL: Send Twilio "clear" command to INSTANTLY stop audio playback
                    # This stops the audio on Twilio's side immediately (send 3x for reliability)
                    async def send_clear_command():
                        try:
                            # Send clear 3x with delays for maximum reliability
                            for _ in range(3):
                                await self.websocket.send_json({
                                    "event": "clear",
                                    "streamSid": self.stream_sid
                                })
                                await asyncio.sleep(0.01)  # 10ms between clears
                            logger.info("🛑 Sent Twilio 'clear' command (3x) - AI audio stopped instantly!")
                        except Exception as e:
                            logger.warning(f"Could not send clear command: {e}")
                    asyncio.create_task(send_clear_command())
                    
                    # CRITICAL: Stop TTS streaming immediately and forcefully
                    if self.tts_streaming_task and not self.tts_streaming_task.done():
                        self.tts_streaming_task.cancel()
                        logger.info("🛑 Cancelled TTS streaming task due to interrupt.")
                    
                    # CRITICAL: Cancel any in-flight speech processing (old questions)
                    # This ensures we only answer the LATEST question, not old ones
                    if self.speech_processing_task and not self.speech_processing_task.done():
                        self.speech_processing_task.cancel()
                        logger.info("🛑 Cancelled previous speech processing - will answer LATEST question only.")
                    
                    # Increment query sequence to invalidate any old queries
                    self.query_sequence += 1
                    logger.info(f"🔄 New interrupt detected, query sequence now: #{self.query_sequence}")
                    
                    # Clear speculative STT state - start fresh
                    self.pending_transcription = ""
                    self.speculative_audio_buffer = bytearray()
                    if self.speculative_stt_task and not self.speculative_stt_task.done():
                        self.speculative_stt_task.cancel()
                    
                    # Set ai_is_speaking to False immediately so interrupt can be processed faster
                    self.ai_is_speaking = False
                    self.ai_speech_start_time = None
                    
                    # CRITICAL: Save the current speech buffer before clearing (for processing later)
                    # This preserves any speech captured before interrupt was validated
                    self.interrupt_speech_buffer = bytes(self.speech_buffer) if self.speech_buffer else b''
                    self.interrupt_frames_captured = self.speech_frames_count
                    logger.info(f"💾 Saved {len(self.interrupt_speech_buffer)} bytes of pre-interrupt speech")
                    
                    # Clear and start fresh for new interrupt speech
                    self.speech_buffer = bytearray()
                    self.speech_frames_count = 0
                    self.silence_frames_count = 0
                    
                    # Start capturing interrupt speech immediately
                    self.speech_buffer.extend(payload)
                    self.speech_frames_count = 1
                    self.is_speaking = True
                    self.interrupt_speech_frames = 0
                    logger.info("🎤 Started capturing interrupt speech (TTS stopped)...")
                    return  # Don't process further in this frame, we've handled the interrupt
                else:
                    # Not enough frames yet - keep tracking but don't process
                    return
            else:
                # No speech detected - reset interrupt tracking
                self.interrupt_speech_frames = 0
                self.interrupt_rms_buffer = []
                return  # Still block all audio while AI is speaking
        
        # Reset interrupt tracking if we're not in interrupt detection mode
        if not self.ai_is_speaking:
            self.interrupt_speech_frames = 0
            self.interrupt_rms_buffer = []
        
        # Normal speech detection and processing
        # If interrupt is detected, allow capturing even if AI is still speaking (TTS is stopping)
        if is_speech:
            self.speech_buffer.extend(payload)
            self.speech_frames_count += 1
            self.silence_frames_count = 0
            self.rms_buffer.append(rms)  # Track RMS for quality validation
            
            # === EDGE CASE: Reset inactivity timer when user speaks ===
            self.last_user_speech_time = time.time()
            self.silence_prompt_sent = False  # Reset prompt flag since user is speaking
            
            # Trigger speculative STT in background (runs every 750ms during speech)
            self._trigger_speculative_stt()
            
            if not self.is_speaking:
                if self.interrupt_detected:
                    logger.info(f"🎤 Capturing interrupt speech (AI stopping), RMS: {rms}...")
                else:
                    logger.info(f"Speech detected (RMS: {rms}).")
                self.is_speaking = True
        elif self.is_speaking:  # Silence after speech
            self.silence_frames_count += 1
            if self.silence_frames_count >= self.SILENCE_THRESHOLD_FRAMES:
                # Only process if AI has stopped speaking (or if it's not an interrupt)
                if self.interrupt_detected and self.ai_is_speaking:
                    # Interrupt detected but TTS hasn't stopped yet - wait
                    logger.info("⏳ Interrupt speech captured, waiting for AI to stop...")
                    return
                
                # PHASE 4: Minimum speech duration check
                if self.speech_frames_count < MIN_SPEECH_DURATION_FRAMES:
                    avg_rms = self._get_average_rms()
                    logger.info(f"🔇 Speech too short ({self.speech_frames_count} frames < {MIN_SPEECH_DURATION_FRAMES}), avg RMS: {avg_rms:.0f}. Ignoring as noise.")
                    self.is_speaking = False
                    self.silence_frames_count = 0
                    self.speech_buffer = bytearray()
                    self.speech_frames_count = 0
                    self.rms_buffer = []
                    self.interrupt_detected = False
                    # Clear speculative STT state
                    self.pending_transcription = ""
                    self.speculative_audio_buffer = bytearray()
                    return
                
                # PHASE 5: Average RMS validation - ensure audio had enough energy
                avg_rms = self._get_average_rms()
                if avg_rms < MIN_RMS_THRESHOLD:
                    logger.info(f"🔇 Average RMS too low ({avg_rms:.0f} < {MIN_RMS_THRESHOLD}), likely noise. Ignoring.")
                    self.is_speaking = False
                    self.silence_frames_count = 0
                    self.speech_buffer = bytearray()
                    self.speech_frames_count = 0
                    self.rms_buffer = []
                    self.interrupt_detected = False
                    # Clear speculative STT state
                    self.pending_transcription = ""
                    self.speculative_audio_buffer = bytearray()
                    return
                
                logger.info(f"Silence threshold reached ({self.speech_frames_count} frames, avg RMS: {avg_rms:.0f}), processing utterance.")
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
                
                # Clear RMS buffer after validation (data is no longer needed)
                self.rms_buffer = []
                
                # Increment query sequence AFTER cancelling previous task
                self.query_sequence += 1
                logger.info(f"🆕 Starting Query #{self.query_sequence}")
                self.speech_processing_task = asyncio.create_task(self._process_user_speech(was_interrupt=was_interrupt))

    async def _run_speculative_stt(self, audio_data: bytes):
        """Run STT in background on current audio.
        Updates pending_transcription with the latest result."""
        try:
            from tools.phone.audio_utils import convert_mulaw_to_wav_bytes
            wav_audio = convert_mulaw_to_wav_bytes(audio_data)
            
            stt_model = self.agent_config.get("sttModel") if self.agent_config else None
            
            # Route to correct STT provider based on model
            if is_deepgram_stt(stt_model):
                # Use Deepgram STT
                stt_tool = get_stt_tool(stt_model)
                result = await stt_tool.transcribe(wav_audio, model=stt_model)
            elif stt_model and stt_model.startswith("elevenlabs"):
                # Use ElevenLabs STT
                stt_tool = get_stt_tool(stt_model)
                result = await stt_tool.transcribe(wav_audio, model=stt_model)
            else:
                # Use OpenAI Whisper (default)
                result = await self.speech_tool.transcribe(wav_audio, "wav", model=stt_model)
            
            transcription = result.get("text", "").strip() if result else ""
            if transcription:
                self.pending_transcription = transcription
                logger.info(f"🔮 Speculative STT: '{transcription[:50]}...' ({len(audio_data)} bytes)")
        except asyncio.CancelledError:
            logger.debug("Speculative STT cancelled")
        except Exception as e:
            logger.warning(f"Speculative STT error: {e}")
    
    def _trigger_speculative_stt(self):
        """Trigger speculative STT if enough time has passed.
        Called from _process_media_event during speech detection."""
        current_time = time.time()
        time_since_last = (current_time - self.last_stt_time) * 1000
        
        # Also add audio to speculative buffer
        if len(self.speech_buffer) > 0:
            self.speculative_audio_buffer = bytearray(self.speech_buffer)  # Copy current buffer
        
        # Check if enough time has passed since last STT
        if time_since_last >= self.SPECULATIVE_STT_INTERVAL_MS and len(self.speculative_audio_buffer) > VAD_FRAME_BYTES * 10:
            # Cancel any existing speculative task
            if self.speculative_stt_task and not self.speculative_stt_task.done():
                self.speculative_stt_task.cancel()
            
            self.last_stt_time = current_time
            # Run STT on current audio buffer
            audio_copy = bytes(self.speculative_audio_buffer)
            self.speculative_stt_task = asyncio.create_task(self._run_speculative_stt(audio_copy))
            logger.debug(f"🔮 Triggered speculative STT ({len(audio_copy)} bytes)")

    async def _process_waiting_interrupt(self):
        """Process interrupt speech that was captured while waiting for TTS to stop.
        This is called when user interrupts the AI (e.g., stops a story to ask a new question).
        The interrupt speech contains the NEW question that should be answered, not the old response."""
        # CRITICAL: Don't wait - process immediately since TTS is already stopped
        logger.info("🔄 Processing interrupt - user asked a NEW question, ignoring previous response.")
        
        # Check if we have enough speech (combine saved + current buffers)
        total_frames = self.speech_frames_count + getattr(self, 'interrupt_frames_captured', 0)
        
        if total_frames < 2:
            logger.info(f"⏭️ Interrupt speech too short ({total_frames} frames), ignoring.")
            self.speech_buffer = bytearray()
            self.speech_frames_count = 0
            self.is_speaking = False
            self.interrupt_detected = False
            return
        
        # CRITICAL: Merge saved interrupt buffer with current buffer for complete speech
        if hasattr(self, 'interrupt_speech_buffer') and self.interrupt_speech_buffer:
            combined_buffer = bytearray(self.interrupt_speech_buffer) + self.speech_buffer
            logger.info(f"📦 Merged interrupt buffers: {len(self.interrupt_speech_buffer)} + {len(self.speech_buffer)} = {len(combined_buffer)} bytes")
            self.speech_buffer = combined_buffer
            self.speech_frames_count = total_frames
            # Clear saved buffer after use
            self.interrupt_speech_buffer = b''
            self.interrupt_frames_captured = 0
        
        logger.info(f"🔄 Processing waiting interrupt: {len(self.speech_buffer)} bytes, {self.speech_frames_count} frames")
        was_interrupt = self.interrupt_detected
        self.interrupt_detected = False
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
            
            # Performance Timing - Start
            perf_start_time = time.perf_counter()
            logger.info(f"⏱️ [PERF] Processing started for Query #{current_query_id}")
            
            # Get audio buffer snapshot (might be empty if already processed)
            if not self.speech_buffer or self.speech_frames_count < 5: # Ignore very short utterances
                if self.is_speaking: logger.info("Ignoring short utterance.")
                self.is_speaking = False
                return

            audio_to_process = self.speech_buffer.copy()
            self.speech_buffer = bytearray()
            self.speech_frames_count = 0
            self.rms_buffer = []  # Clear RMS buffer after capturing audio
            
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
                logger.info(f"═══════════════════════════════════════════════════")
                logger.info(f"🔊 STEP 1: Audio received from Twilio ({len(audio_to_process)} bytes mu-law)")
                wav_audio_data = convert_mulaw_to_wav_bytes(audio_to_process)
                logger.info(f"   ✅ Converted to WAV: {len(wav_audio_data)} bytes")
                
                # Use agent config for STT if available
                stt_model_to_use = self.agent_config.get("sttModel") if self.agent_config else None
                supported_languages = self.agent_config.get("supportedLanguages", ["en"]) if self.agent_config else ["en"]
                primary_language = supported_languages[0] if supported_languages else "en"
                logger.info(f"   📞 STT model: {stt_model_to_use or 'whisper-1'}, languages: {supported_languages}")
                
                # 1. Transcribe speech - USE SPECULATIVE RESULT IF AVAILABLE
                perf_stt_start = time.perf_counter()
                
                # Check if we have a pending transcription from speculative STT
                if self.pending_transcription and len(self.pending_transcription) > 3:
                    # Use the speculative transcription (already processed in background!)
                    user_text = self.pending_transcription
                    detected_language = primary_language  # Assume primary for speculative
                    perf_stt_end = time.perf_counter()
                    stt_duration = (perf_stt_end - perf_stt_start) * 1000
                    logger.info(f"⚡ Using SPECULATIVE transcription (0ms STT!): '{user_text[:50]}...'")
                    # Clear pending transcription after use
                    self.pending_transcription = ""
                    self.speculative_audio_buffer = bytearray()
                    # Cancel speculative task if still running
                    if self.speculative_stt_task and not self.speculative_stt_task.done():
                        self.speculative_stt_task.cancel()
                else:
                    # No speculative result - run STT synchronously
                    # Route to correct STT provider based on model
                    if is_deepgram_stt(stt_model_to_use):
                        # Use Deepgram STT (Nova)
                        logger.info(f"🎤 Using Deepgram STT: {stt_model_to_use} (lang hint: {primary_language})")
                        stt_tool = get_stt_tool(stt_model_to_use)
                        stt_result = await stt_tool.transcribe(
                            wav_audio_data,
                            model=stt_model_to_use,
                            language=primary_language
                        )
                    elif stt_model_to_use and stt_model_to_use.startswith("elevenlabs"):
                        # Use ElevenLabs STT (Scribe)
                        logger.info(f"🎙️ Using ElevenLabs STT: {stt_model_to_use} (lang hint: {primary_language})")
                        stt_tool = get_stt_tool(stt_model_to_use)
                        stt_result = await stt_tool.transcribe(
                            wav_audio_data,
                            model=stt_model_to_use,
                            language_code=primary_language
                        )
                    else:
                        # Use OpenAI Whisper (default)
                        logger.info(f"🤖 Using OpenAI Whisper STT: {stt_model_to_use or 'whisper-1'} (lang hint: {primary_language})")
                        stt_result = await self.speech_tool.transcribe(
                            wav_audio_data,
                            "wav",
                            model=stt_model_to_use,
                            language=primary_language
                        )
                    user_text = stt_result.get("text", "").strip()
                    detected_language = stt_result.get("detected_language", primary_language)
                    perf_stt_end = time.perf_counter()
                    stt_duration = (perf_stt_end - perf_stt_start) * 1000
                    # Clear speculative state
                    self.pending_transcription = ""
                    self.speculative_audio_buffer = bytearray()
                
                # NOTE: Language validation DISABLED - STT detection is unreliable for phone audio
                # The language hint is passed to STT for accuracy, but we don't reject based on detection
                # if detected_language and not is_language_supported(detected_language, supported_languages):
                #     ...rejected speech here...
                
                if not user_text:
                    logger.info("STT result is empty, skipping AI response.")
                    return
                
                # PHASE 5: Post-STT validation - filter out noise transcriptions
                if not self._is_valid_transcript(user_text):
                    logger.info(f"🔇 Invalid transcript filtered: '{user_text}' - skipping AI response (taking {stt_duration:.0f}ms)")
                    return
                
                # CRITICAL: Verify this is still the current query before proceeding
                # If query_sequence changed, this query is outdated and should be skipped
                if current_query_id != self.query_sequence:
                    logger.info(f"⏭️ Skipping outdated query #{current_query_id} after STT (current: #{self.query_sequence})")
                    return
                
                if was_interrupt:
                    logger.info(f"🔄 Interrupt transcription (Query #{current_query_id}): '{user_text}' (STT: {stt_duration:.0f}ms)")
                else:
                    logger.info(f"User said (Query #{current_query_id}): '{user_text}' (STT: {stt_duration:.0f}ms)")
                logger.info(f"📝 STEP 2: STT Complete - '{user_text[:80]}...' ({stt_duration:.0f}ms)")
                
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
                llm_model_to_use = self.agent_config.get("inferenceModel") if self.agent_config else None
                temperature = self.agent_config.get("temperature") if self.agent_config else None
                # OPTIMIZATION: Default to 200 max_tokens for faster, more conversational responses
                max_tokens = self.agent_config.get("maxTokens", 200) if self.agent_config else 200
                
                # CRITICAL: Pass the current session_data which contains the full conversation history
                # The conversation_tool.generate_response will use this history to provide context
                # For interrupts, this ensures the AI answers the NEW question using conversation history
                if was_interrupt:
                    logger.info(f"🔄 Generating response for INTERRUPT question using conversation history...")
                    logger.info(f"   Question: '{user_text[:100]}...'")
                    logger.info(f"   History: {len(conversation_history)} previous interactions will be used for context")
                
                # 2. Get AI response
                system_prompt = self.agent_config.get("systemPrompt", "You are a helpful AI assistant.")
                
                # Update session prompt if changed
                if self.session_data.get("prompt") != system_prompt:
                    self.session_data["prompt"] = system_prompt
                
                logger.info(f"🧠 STEP 3: Sending to LLM ({llm_model_to_use or 'gpt-4o-mini'})")
                perf_llm_start = time.perf_counter()
                
                # OPTIMIZATION: Use streaming LLM → TTS pipeline for real-time response
                # AI starts speaking within ~0.8s instead of waiting for full LLM completion (~2.5s)
                logger.info(f"   Starting STREAMING LLM → TTS pipeline (Query #{current_query_id})")
                
                # Get conversation history for streaming
                conversation_history = self.session_data.get("conversation_history", [])
                
                # Track full response for history
                full_response = ""
                sentence_count = 0
                first_sentence_time = None
                
                # Stream sentences from LLM and pipe to TTS in real-time
                # CRITICAL: Await each TTS immediately as sentence arrives (sequential audio)
                # This gives us low TTFS while ensuring audio plays in correct order
                async for sentence in self.conversation_tool.conversation_manager._generate_response_streaming(
                    context="",  # Context is built internally by the streaming method
                    user_input=user_text,
                    conversation_history=conversation_history,
                    persona_config=None,
                    model=llm_model_to_use,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    custom_system_prompt=system_prompt
                ):
                    # Check if query was cancelled during streaming
                    if current_query_id != self.query_sequence:
                        logger.info(f"⏭️ Query #{current_query_id} cancelled during streaming")
                        return
                    
                    # CRITICAL: Check for interrupt BEFORE processing next sentence
                    if self.interrupt_detected:
                        logger.info(f"🛑 Interrupt detected in streaming loop, stopping pipeline immediately")
                        # Cancel any running TTS task
                        if self.tts_streaming_task and not self.tts_streaming_task.done():
                            self.tts_streaming_task.cancel()
                        return
                    
                    # Skip very short fragments (like "1.", "2.", etc.)
                    if len(sentence.strip()) < 5:
                        full_response += (" " if full_response else "") + sentence
                        continue
                    
                    sentence_count += 1
                    full_response += (" " if full_response else "") + sentence
                    
                    # Record time to first sentence (TTFS - Time To First Speech)
                    if sentence_count == 1:
                        first_sentence_time = time.perf_counter()
                        ttfs_ms = (first_sentence_time - perf_llm_start) * 1000
                        logger.info(f"⚡ TTFS (Time To First Speech): {ttfs_ms:.0f}ms - AI starting to speak!")
                    
                    # Check again right before TTS
                    if self.interrupt_detected:
                        logger.info(f"🛑 Interrupt detected before TTS, stopping immediately")
                        return
                    
                    # IMMEDIATELY await TTS for this sentence
                    # Handle CancelledError from interrupt detection
                    logger.info(f"🎤 Sentence #{sentence_count} → TTS: '{sentence[:50]}...'")
                    self.tts_streaming_task = asyncio.create_task(self._synthesize_and_stream_tts(sentence))
                    try:
                        await self.tts_streaming_task
                    except asyncio.CancelledError:
                        logger.info(f"🛑 TTS task cancelled by interrupt, stopping streaming pipeline")
                        return
                    
                    # Check after TTS completes - stop if interrupted during TTS
                    if self.interrupt_detected:
                        logger.info(f"🛑 Interrupt detected after TTS, stopping streaming")
                        return
                
                perf_llm_end = time.perf_counter()
                llm_duration = (perf_llm_end - perf_llm_start) * 1000
                total_duration_so_far = (perf_llm_end - perf_start_time) * 1000
                
                response_text = full_response.strip()
                
                logger.info(f"🤖 AI Response (STREAMED): {response_text[:70]}... (Total: {llm_duration:.0f}ms, {sentence_count} sentences)")
                logger.info(f"⏱️ [PERF] LLM+TTS Complete: +{llm_duration:.0f}ms (Total: {total_duration_so_far:.0f}ms)")
                
                # CRITICAL: Verify this is still the current query before updating session
                if current_query_id != self.query_sequence:
                    logger.info(f"⏭️ Skipping outdated query #{current_query_id} after streaming complete (current: #{self.query_sequence})")
                    return
                
                # Update session with full response for conversation history
                # CRITICAL: Manually update conversation history since we used streaming
                self.session_data = self.conversation_tool.add_to_conversation_history(
                    self.session_data, user_text, response_text
                )
                
                old_history_count = len(conversation_history)
                new_history_count = len(self.session_data.get("conversation_history", []))
                logger.info(f"✅ Updated session_data (Query #{current_query_id}): {old_history_count} → {new_history_count} interactions")
                
                if was_interrupt:
                    logger.info(f"💬 AI responded to INTERRUPT (Query #{current_query_id}): '{response_text[:70]}...'")
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
                
                logger.info(f"✅ Streaming pipeline completed for Query #{current_query_id}")
                
                # Check if call should end after this response (farewell phrases)
                if self._should_end_call(response_text):
                    logger.info(f"👋 Farewell phrase detected, scheduling call hangup for {self.call_sid}")
                    await asyncio.sleep(1.5)  # Give time for audio to finish
                    try:
                        await self.hangup_call(reason="Farewell phrase detected")
                        logger.info(f"📱 Call {self.call_sid} ended after farewell")
                    except Exception as e:
                        logger.warning(f"Could not auto-hangup after farewell: {e}")

            except asyncio.CancelledError:
                logger.info(f"🛑 Speech processing task #{current_query_id} was cancelled.")
                raise
            except Exception as e:
                logger.error(f"Error processing user speech (Query #{current_query_id}): {e}", exc_info=True)

    def _split_for_fast_tts(self, text: str) -> List[str]:
        """Split text into small TTS-friendly chunks for faster interrupt response.
        
        Splits at sentence boundaries, commas, semicolons to create ~50-80 char chunks.
        Ensures interrupt checks happen frequently during long AI responses.
        """
        import re
        chunks = []
        
        # First split into sentences
        sentences = self.tts_tool._split_into_sentences(text)
        
        for sentence in sentences:
            if len(sentence) > 80:
                # Split long sentences at punctuation
                parts = re.split(r'([,;:])', sentence)
                current_chunk = ""
                for i, part in enumerate(parts):
                    if part in [',', ';', ':']:
                        current_chunk += part
                    elif len(current_chunk) + len(part) < 80:
                        current_chunk += part
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = part
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
            else:
                chunks.append(sentence)
        
        return [c for c in chunks if c.strip()]

    async def _synthesize_with_interrupt_check(self, text: str, voice: str, model: str = None):
        """Synthesize TTS with periodic interrupt checking (every 50ms).
        
        Returns None if interrupted during synthesis, allowing fast abort.
        """
        # Start TTS synthesis in background task
        tts_task = asyncio.create_task(self._synthesize_pcm(text, voice=voice, model=model))
        
        # Poll for interrupt while TTS is running
        while not tts_task.done():
            if self.interrupt_detected:
                tts_task.cancel()
                logger.info(f"🛑 TTS cancelled mid-synthesis due to interrupt! (chunk: '{text[:30]}...')")
                try:
                    await tts_task
                except asyncio.CancelledError:
                    pass
                return None
            await asyncio.sleep(0.05)  # Check every 50ms
        
        return tts_task.result()

    async def _send_greeting(self):
        """Generates and streams a greeting message to the caller. For outbound calls, AI drives the conversation.
        Implements call settling and greeting lock for human-like conversation flow."""
        try:
            # PHASE 1: Call settling period - let the call fully connect before any audio processing
            logger.info(f"⏳ Call settling period starting for call {self.call_sid}...")
            await asyncio.sleep(0.5)  # 500ms settling period for all calls
            self.call_settling_complete = True
            
            # === EDGE CASE: Start tracking call duration ===
            self.call_start_time = time.time()
            logger.info(f"✅ Call settled, ready to send greeting for call {self.call_sid}")
            
            # Check if agent_config is available
            if not self.agent_config:
                logger.error(f"❌ Cannot send greeting: agent_config is None for call {self.call_sid}")
                self.greeting_complete = True  # Allow listening even if greeting fails
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
            
            # PHASE 2: Greeting complete - now enable speech detection
            self.greeting_complete = True
            logger.info(f"🎤 Greeting complete, now listening for user speech (call {self.call_sid})")
            
            # === EDGE CASE: Start inactivity monitoring ===
            # Initialize last user speech time to now (give user time to respond after greeting)
            self.last_user_speech_time = time.time()
            self.inactivity_check_task = asyncio.create_task(self._monitor_inactivity())
            logger.info(f"⏰ Started inactivity monitoring for call {self.call_sid}")
            
        except Exception as e:
            logger.error(f"❌ Error sending greeting for call {self.call_sid}: {e}", exc_info=True)
            # Enable listening even if greeting fails
            self.greeting_complete = True
            self.call_settling_complete = True

    async def _monitor_inactivity(self):
        """Background task to monitor for user inactivity and max call duration.
        
        DEFENSIVE: Only checks when call is truly idle (not during speech/processing).
        Checks every 5 seconds:
        - If user hasn't spoken for PROMPT_AFTER_SILENCE_SECONDS: send "Are you still there?" prompt
        - If user hasn't spoken for INACTIVITY_TIMEOUT_SECONDS: hangup with farewell
        - If call exceeds MAX_CALL_DURATION_SECONDS: hangup with farewell
        """
        logger.info(f"⏰ Inactivity monitor started for call {self.call_sid}")
        
        try:
            while True:
                await asyncio.sleep(5)  # Check every 5 seconds (less aggressive)
                
                # === DEFENSIVE CHECKS: Skip if call is actively in use ===
                # Skip if AI is speaking (user waiting for response)
                if self.ai_is_speaking:
                    continue
                
                # Skip if user is currently speaking
                if self.is_speaking:
                    continue
                
                # Skip if speech is being processed
                if self.speech_processing_task and not self.speech_processing_task.done():
                    continue
                
                # Skip if TTS is being processed
                if self.tts_streaming_task and not self.tts_streaming_task.done():
                    continue
                
                current_time = time.time()
                
                # === Check max call duration (safety limit) ===
                if self.call_start_time:
                    call_duration = current_time - self.call_start_time
                    if call_duration >= self.MAX_CALL_DURATION_SECONDS:
                        logger.warning(f"⏰ Max call duration ({self.MAX_CALL_DURATION_SECONDS}s) reached for call {self.call_sid}")
                        await self._hangup_call(
                            reason="max_duration",
                            farewell_message="I have to end our call now. Thank you for your time. Goodbye!"
                        )
                        return  # Stop monitoring
                
                # === Check user inactivity (only if not during active conversation) ===
                if self.last_user_speech_time:
                    silence_duration = current_time - self.last_user_speech_time
                    
                    # Check if user has been silent too long (total timeout)
                    if silence_duration >= self.INACTIVITY_TIMEOUT_SECONDS:
                        logger.warning(f"⏰ User inactivity timeout ({self.INACTIVITY_TIMEOUT_SECONDS}s) reached for call {self.call_sid}")
                        await self._hangup_call(
                            reason="inactivity",
                            farewell_message="It seems like you're not there. I'll end the call now. Goodbye!"
                        )
                        return  # Stop monitoring
                    
                    # Check if we should prompt for activity (only once per silence period)
                    if silence_duration >= self.PROMPT_AFTER_SILENCE_SECONDS and not self.silence_prompt_sent:
                        logger.info(f"⏰ User silence ({silence_duration:.0f}s), sending prompt for call {self.call_sid}")
                        self.silence_prompt_sent = True
                        
                        # Send "are you still there?" prompt
                        try:
                            await self._synthesize_and_stream_tts("Are you still there? I'm here to help.")
                            # DON'T reset timer - let inactivity timeout proceed to hangup
                        except Exception as e:
                            logger.warning(f"Error sending silence prompt: {e}")
                
        except asyncio.CancelledError:
            logger.info(f"⏰ Inactivity monitor cancelled for call {self.call_sid}")
        except Exception as e:
            # Don't let monitor errors crash the call
            logger.error(f"⏰ Inactivity monitor error for call {self.call_sid}: {e}", exc_info=True)

    async def _hangup_call(self, reason: str = "normal", farewell_message: Optional[str] = None):
        """Gracefully hang up the call with optional farewell message.
        
        Args:
            reason: Reason for hangup (for logging)
            farewell_message: Optional message to say before hanging up
        """
        logger.info(f"📞 Hanging up call {self.call_sid} - reason: {reason}")
        
        try:
            # Send farewell message if provided
            if farewell_message:
                logger.info(f"📢 Sending farewell: '{farewell_message}'")
                await self._synthesize_and_stream_tts(farewell_message)
                await asyncio.sleep(0.5)  # Give time for message to play
            
            # Cancel inactivity monitor if running
            if self.inactivity_check_task and not self.inactivity_check_task.done():
                self.inactivity_check_task.cancel()
            
            # Use Twilio REST API to end the call
            try:
                from utils.twilio_credentials import get_twilio_credentials
                
                # Get credentials from stored phone number
                twilio_creds = await get_twilio_credentials(phone_number=self.to_number, call_sid=self.call_sid)
                if twilio_creds:
                    from twilio.rest import Client
                    client = Client(twilio_creds["account_sid"], twilio_creds["auth_token"])
                    client.calls(self.call_sid).update(status="completed")
                    logger.info(f"✅ Call {self.call_sid} ended via Twilio API")
                else:
                    # Fallback: close websocket to end stream
                    logger.info(f"⚠️ No Twilio creds, closing websocket for call {self.call_sid}")
                    await self.websocket.close()
            except Exception as e:
                logger.warning(f"Could not end call via API, closing websocket: {e}")
                try:
                    await self.websocket.close()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error in _hangup_call for {self.call_sid}: {e}", exc_info=True)

    async def _synthesize_and_stream_tts(self, text: str):
        """Synthesizes text to speech and streams it back to Twilio using fast PCM conversion.
        Supports interruption - will stop streaming if user interrupts."""
        logger.info(f"🔈 STEP 4: TTS Synthesis - '{text[:50]}...'")
        
        # Track if this is the first sentence of a new response (for calibration)
        is_new_response = not self.ai_is_speaking
        
        # Set flag to prevent processing incoming audio (feedback loop prevention)
        self.ai_is_speaking = True
        self.ai_speech_start_time = time.time()  # Record when AI started speaking (for grace period)
        
        # Only reset noise calibration for FIRST sentence of a response
        # This prevents AI echo from corrupting calibration on subsequent sentences
        if is_new_response:
            self.noise_calibration_buffer = []
            self.noise_calibration_complete = False
            self.dynamic_interrupt_threshold = MIN_INTERRUPT_RMS_THRESHOLD
            logger.info("   🔇 AI started NEW response, muting user + starting noise calibration")
        else:
            logger.info("   🔇 AI continuing multi-sentence response (keeping existing calibration)")
        
        # Get agent config for TTS if available
        tts_voice = self.agent_config.get("ttsVoice", "alloy") if self.agent_config else "alloy"
        tts_model = self.agent_config.get("ttsModel") if self.agent_config else None
        logger.info(f"   🎙️ TTS model: {tts_model or 'tts-1'}, voice: {tts_voice}")
        
        try:
            # Split into smaller chunks for faster interrupt response
            chunks = self._split_for_fast_tts(text)
            logger.info(f"   📝 Split into {len(chunks)} TTS chunks for fast interrupt")
            
            for chunk in chunks:
                # CRITICAL: Check for interrupt before processing each chunk
                if self.interrupt_detected:
                    logger.info("🛑 TTS interrupted by user, stopping stream immediately.")
                    self.ai_is_speaking = False
                    self.ai_speech_start_time = None
                    return
                
                if not chunk.strip():
                    continue
                
                # Synthesize with interrupt polling (checks every 50ms during synthesis)
                # SPECIAL PATH for Deepgram Streaming (Low Latency)
                if is_deepgram_tts(tts_model):
                    await self._stream_deepgram_tts(chunk, tts_voice, tts_model)
                    # If interrupted during streaming, the helper sets self.ai_is_speaking = False
                    if not self.ai_is_speaking:
                         return
                    continue # Move to next chunk

                # ORIGINAL PATH for other providers (OpenAI, ElevenLabs)
                perf_tts_chunk_start = time.perf_counter()
                tts_result = await self._synthesize_with_interrupt_check(chunk, voice=tts_voice, model=tts_model)
                perf_tts_chunk_end = time.perf_counter()
                
                # If interrupted during synthesis, tts_result will be None
                if tts_result is None or self.interrupt_detected:
                    logger.info("🛑 TTS interrupted during synthesis, stopping stream.")
                    self.ai_is_speaking = False
                    return
                
                logger.info(f"⏱️ [PERF] TTS Chunk Generated: +{(perf_tts_chunk_end - perf_tts_chunk_start)*1000:.0f}ms (Chunk: '{chunk[:20]}...')")
                
                if tts_result.get("success"):
                    # CRITICAL: Check for interrupt BEFORE sending audio chunk
                    if self.interrupt_detected:
                        logger.info("🛑 Interrupt detected before sending audio chunk, stopping immediately.")
                        self.ai_is_speaking = False
                        return
                    
                    audio_bytes = tts_result["audio_bytes"]
                    # CRITICAL: Check for interrupt BEFORE conversion (saves processing time)
                    if self.interrupt_detected:
                        logger.info("🛑 Interrupt detected before audio conversion, stopping immediately.")
                        self.ai_is_speaking = False
                        return
                    
                    # Check if audio is already in mulaw format (e.g., from Deepgram)
                    if tts_result.get("is_mulaw"):
                        # Skip conversion - audio is already mulaw from Deepgram
                        mulaw_bytes = audio_bytes
                        logger.info(f"📡 Using pre-converted mulaw audio from Deepgram: {len(mulaw_bytes)} bytes")
                    else:
                        # Fast conversion: PCM -> mu-law using only Python audioop (no ffmpeg)
                        mulaw_bytes = convert_pcm_to_mulaw(audio_bytes, input_rate=24000, input_width=2)
                    if mulaw_bytes:
                        logger.info(f"📡 STEP 5: Sending {len(mulaw_bytes)} bytes audio to Twilio")
                        # CHUNKED AUDIO: Split into 100ms chunks (8kHz * 0.1s = 800 bytes)
                        # Ultra-small chunks for instant interrupt response
                        CHUNK_SIZE = 800  # 100ms at 8kHz mu-law - instant interrupt response
                        
                        for chunk_start in range(0, len(mulaw_bytes), CHUNK_SIZE):
                            # Check for interrupt BEFORE each chunk
                            if self.interrupt_detected:
                                logger.info(f"🛑 Interrupt detected at chunk {chunk_start//CHUNK_SIZE}, stopping audio immediately.")
                                self.ai_is_speaking = False
                                return
                            
                            chunk = mulaw_bytes[chunk_start:chunk_start + CHUNK_SIZE]
                            payload = base64.b64encode(chunk).decode('utf-8')
                            
                            await self.websocket.send_json({
                                "event": "media",
                                "streamSid": self.stream_sid,
                                "media": {"payload": payload}
                            })
                            
                            # Small yield to allow interrupt detection between chunks
                            await asyncio.sleep(0.01)
                else:
                    logger.error(f"TTS failed for chunk: {chunk}")

            # Only send end mark if we weren't interrupted
            if not self.interrupt_detected:
                # Send mark to signal end of speech (will trigger ai_is_speaking = False in mark handler)
                await self.websocket.send_json({
                    "event": "mark",
                    "streamSid": self.stream_sid,
                    "mark": {"name": "end_of_ai_speech"}
                })
                logger.info("✅ COMPLETE: Audio streamed to Twilio successfully")
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
        """Generate TTS in PCM format for fast streaming (no conversion overhead).
        
        Supports both OpenAI and ElevenLabs TTS providers based on model name.
        """
        try:
            # Use provided voice/model or fall back to agent config or defaults
            tts_voice = voice or (self.agent_config.get("ttsVoice", "alloy") if self.agent_config else "alloy")
            tts_model = model or (self.agent_config.get("ttsModel") if self.agent_config else self.tts_tool.model)
            
            # Check provider based on model name
            if is_deepgram_tts(tts_model):
                # Use Deepgram Aura TTS
                logger.info(f"🔊 Using Deepgram TTS: model={tts_model}, voice={tts_voice}")
                deepgram_tts = get_tts_tool(tts_model)
                # Deepgram returns mulaw bytes directly for Twilio
                audio_bytes = deepgram_tts.synthesize_pcm(
                    text=text,
                    voice=tts_voice,
                    sample_rate=8000
                )
                # Return in format compatible with existing code
                # Note: Deepgram synthesize_pcm returns raw mulaw bytes, not PCM
                # We need to signal this so conversion is skipped
                return {
                    "success": True if audio_bytes else False,
                    "audio_bytes": audio_bytes,
                    "is_mulaw": True  # Signal that this is already mulaw, skip PCM conversion
                }
            elif is_elevenlabs_tts(tts_model):
                # Use ElevenLabs TTS
                logger.info(f"🎙️ Using ElevenLabs TTS: model={tts_model}, voice={tts_voice}")
                elevenlabs_tts = get_tts_tool(tts_model)
                result = await elevenlabs_tts.synthesize_pcm(
                    text=text,
                    voice=tts_voice,
                    model=tts_model
                )
                return result
            else:
                # Use OpenAI TTS (default)
                logger.info(f"🤖 Using OpenAI TTS: model={tts_model or 'tts-1'}, voice={tts_voice}")
                response = self.tts_tool.client.audio.speech.create(
                    model=tts_model or "tts-1",
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

    async def _handle_stop_event(self, stop_data: Dict):
        """Handles the 'stop' event from Twilio stream."""
        logger.info(f"Stream stopped for call SID: {self.call_sid}. Cleaning up.")
        
        # End call in MongoDB - await to ensure it completes
        try:
            from databases.mongodb_call_store import MongoDBCallStore
            call_store = MongoDBCallStore()
            result = await call_store.end_call(self.call_sid)
            if result:
                logger.info(f"✅ Call {self.call_sid} marked as completed in MongoDB")
            else:
                logger.warning(f"⚠️ Failed to mark call {self.call_sid} as completed")
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
    async def _stream_deepgram_tts(self, text: str, voice: str, model: str):
        """Dedicated streaming path for Deepgram to minimize latency."""
        try:
            logger.info(f"🌊 Streaming Deepgram TTS: '{text[:20]}...'")
            deepgram_tts = get_tts_tool(model)
            
            # 1. Start generation (returns iterator immediately)
            # Use 'mulaw' encoding directly from Deepgram to skip conversion
            audio_iterator = await deepgram_tts.synthesize_stream(
                text=text,
                voice=voice,
                encoding="mulaw",
                sample_rate=8000
            )
            
            # 2. Iterate and send chunks immediately
            # Deepgram creates small chunks suitable for streaming
            count = 0
            for chunk_bytes in audio_iterator:
                # CRITICAL: Check interrupt between every network chunk
                if self.interrupt_detected:
                    logger.info("🛑 Interrupt detected during Deepgram stream, stopping.")
                    self.ai_is_speaking = False
                    return

                if not chunk_bytes:
                    continue

                # 3. Send directly (no conversion needed for mulaw)
                payload = base64.b64encode(chunk_bytes).decode('utf-8')
                
                await self.websocket.send_json({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": payload}
                })
                
                # Update mark if this is the first chunk?
                # Actually we send mark *after* all audio... 
                # but we need to track if we sent anything.
                count += 1
                
            logger.info(f"✅ Deepgram stream complete ({count} chunks)")

        except Exception as e:
            logger.error(f"❌ Error in Deepgram streaming: {e}")
            # Don't crash, just log. Caller loop continues.
