import asyncio
import json
import base64
import logging
import time
from fastapi import WebSocket
from typing import Dict, Any

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

    def __init__(self, websocket: WebSocket, speech_tool: SpeechToTextTool, tts_tool: TextToSpeechTool, conversation_tool: ConversationalResponseTool):
        self.websocket = websocket
        self.speech_tool = speech_tool
        self.tts_tool = tts_tool
        self.conversation_tool = conversation_tool
        
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
        self.SILENCE_THRESHOLD_FRAMES = 25  # 25 frames * 20ms/frame = 500ms of silence to trigger processing
        self.INTERRUPT_GRACE_PERIOD_MS = 800  # Wait 800ms after AI starts speaking before allowing interrupts (prevents feedback loop)

    async def handle_stream(self):
        """Main loop to receive and process audio from the Twilio media stream."""
        logger.info("New Twilio stream connection handler created.")
        while True:
            message = await self.websocket.receive_text()
            data = json.loads(message)

            event = data.get('event')
            if event == 'start':
                self._handle_start_event(data['start'])
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
                    self.ai_is_speaking = False
                    self.ai_speech_start_time = None
                    logger.info("✅ AI finished speaking, listening for user now.")

    def _handle_start_event(self, start_data: Dict):
        """Handles the 'start' event from Twilio stream."""
        self.stream_sid = start_data['streamSid']
        self.call_sid = start_data['callSid']
        from_number = start_data.get('customParameters', {}).get('From', 'Unknown')
        to_number = start_data.get('customParameters', {}).get('To', 'Unknown')
        
        logger.info(f"Stream started: call_sid={self.call_sid}, stream_sid={self.stream_sid}")
        logger.info(f"Call from: {from_number} to: {to_number}")

        # Create a session for the call
        session_info = self.conversation_tool.create_session(customer_id=f"phone_{from_number}")
        self.session_id = session_info.get("session_id")
        self.session_data = session_info

    def _process_media_event(self, media_data: Dict):
        """Processes incoming 'media' events using VAD. Supports interrupt detection."""
        payload = base64.b64decode(media_data['payload'])
        
        # VAD expects 160-byte chunks for 8kHz, 20ms frames
        if len(payload) != VAD_FRAME_BYTES:
            logger.warning(f"Received unexpected payload size: {len(payload)}. Expected {VAD_FRAME_BYTES}")
            return

        is_speech = self.vad.is_speech(payload, VAD_SAMPLE_RATE)
        
        # INTERRUPT DETECTION: If AI is speaking and user starts talking, interrupt!
        # BUT: Only allow interrupts after grace period to prevent AI feedback loop
        if is_speech and self.ai_is_speaking and not self.interrupt_detected:
            # Check if grace period has passed (prevents AI from hearing its own voice)
            if self.ai_speech_start_time:
                elapsed_ms = (time.time() - self.ai_speech_start_time) * 1000
                if elapsed_ms < self.INTERRUPT_GRACE_PERIOD_MS:
                    # Still in grace period - ignore this speech (likely AI feedback)
                    return
            
            # Grace period passed - this is a real user interrupt!
            logger.info("🚨 INTERRUPT DETECTED: User is speaking while AI is talking!")
            self.interrupt_detected = True
            # Stop TTS streaming immediately
            if self.tts_streaming_task and not self.tts_streaming_task.done():
                self.tts_streaming_task.cancel()
                logger.info("🛑 Cancelled TTS streaming task due to interrupt.")
            # Clear AI speaking flag to allow processing interrupt
            self.ai_is_speaking = False
            self.ai_speech_start_time = None
            # Clear any existing speech buffer to start fresh
            self.speech_buffer = bytearray()
            self.speech_frames_count = 0
            self.silence_frames_count = 0
        
        # If AI is speaking and no interrupt, ignore audio (prevent feedback loop)
        if self.ai_is_speaking and not self.interrupt_detected:
            return
        
        # Normal speech detection and processing
        if is_speech:
            self.speech_buffer.extend(payload)
            self.speech_frames_count += 1
            self.silence_frames_count = 0
            if not self.is_speaking:
                logger.info("Speech detected.")
                self.is_speaking = True
        elif self.is_speaking:  # Silence after speech
            self.silence_frames_count += 1
            if self.silence_frames_count >= self.SILENCE_THRESHOLD_FRAMES:
                logger.info("Silence threshold reached after speech, processing utterance.")
                self.is_speaking = False
                self.silence_frames_count = 0
                # Reset interrupt flag after processing
                was_interrupt = self.interrupt_detected
                self.interrupt_detected = False
                asyncio.create_task(self._process_user_speech(was_interrupt=was_interrupt))

    async def _process_user_speech(self, was_interrupt: bool = False):
        """Transcribes the buffered speech, gets an AI response, and streams TTS back."""
        if not self.speech_buffer or self.speech_frames_count < 5: # Ignore very short utterances
            self.speech_buffer = bytearray()
            self.speech_frames_count = 0
            if self.is_speaking: logger.info("Ignoring short utterance.")
            self.is_speaking = False
            return

        audio_to_process = self.speech_buffer
        self.speech_buffer = bytearray()
        self.speech_frames_count = 0
        
        if was_interrupt:
            logger.info(f"🔄 Processing INTERRUPT speech: {len(audio_to_process)} bytes")
        else:
            logger.info(f"Processing {len(audio_to_process)} bytes of speech.")

        try:
            wav_audio_data = convert_mulaw_to_wav_bytes(audio_to_process)
            stt_result = await self.speech_tool.transcribe(wav_audio_data, "wav")
            user_text = stt_result.get("text", "").strip()

            if not user_text:
                logger.info("STT result is empty, skipping AI response.")
                return
            
            if was_interrupt:
                logger.info(f"🔄 Interrupt transcription: '{user_text}'")
            else:
                logger.info(f"User said: '{user_text}'")
            
            ai_response = await self.conversation_tool.generate_response(self.session_data, user_text, None)
            response_text = ai_response.get("response", "I'm sorry, I'm having trouble with that.")
            logger.info(f"AI response: '{response_text[:70]}...'")
            
            # Store TTS task so it can be cancelled if interrupted
            self.tts_streaming_task = asyncio.create_task(self._synthesize_and_stream_tts(response_text))
            try:
                await self.tts_streaming_task
            except asyncio.CancelledError:
                logger.info("🛑 TTS task was cancelled (interrupt handled).")
        except Exception as e:
            logger.error(f"Error processing user speech: {e}", exc_info=True)

    async def _send_greeting(self):
        """Generates and streams a greeting message to the caller."""
        greeting_text = "Hello! How can I help you today?"
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
                tts_result = await self._synthesize_pcm(sentence)
                
                # Check again after TTS generation (user might have interrupted during generation)
                if self.interrupt_detected:
                    logger.info("🛑 TTS interrupted after generation, stopping stream.")
                    self.ai_is_speaking = False
                    return
                
                if tts_result.get("success"):
                    pcm_bytes = tts_result["audio_bytes"]
                    # Fast conversion: PCM -> mu-law using only Python audioop (no ffmpeg)
                    mulaw_bytes = convert_pcm_to_mulaw(pcm_bytes, input_rate=24000, input_width=2)
                    if mulaw_bytes:
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
                logger.info("✅ TTS stream interrupted, ready for user input.")
        except asyncio.CancelledError:
            logger.info("🛑 TTS streaming task was cancelled (interrupt).")
            self.ai_is_speaking = False
            self.ai_speech_start_time = None
            raise
        except Exception as e:
            logger.error(f"Error in TTS streaming: {e}", exc_info=True)
            # Make sure to re-enable listening even if TTS fails
            self.ai_is_speaking = False
            self.ai_speech_start_time = None
            logger.info("✅ AI speech error, re-enabling user audio.")
    
    async def _synthesize_pcm(self, text: str) -> Dict[str, Any]:
        """Generate TTS in PCM format for fast streaming (no conversion overhead)."""
        try:
            response = self.tts_tool.client.audio.speech.create(
                model=self.tts_tool.model,
                voice="alloy",
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

    def _handle_stop_event(self, stop_data: Dict):
        """Handles the 'stop' event from Twilio stream."""
        logger.info(f"Stream stopped for call SID: {self.call_sid}. Cleaning up.")
        # Any final cleanup can go here.
