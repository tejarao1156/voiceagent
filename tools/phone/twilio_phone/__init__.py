"""Twilio Phone Tool for handling incoming phone calls with AI conversation.

This tool integrates Twilio Voice API with the existing voice agent tools
to enable AI-powered phone conversations.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse

if TYPE_CHECKING:  # pragma: no cover
    from tools.understanding.speech_to_text import SpeechToTextTool
    from tools.response.text_to_speech import TextToSpeechTool
    from tools.response.conversation import ConversationalResponseTool

from tools.phone.twilio_phone.audio_converter import twilio_to_wav, wav_to_twilio
from config import TWILIO_WEBHOOK_BASE_URL

logger = logging.getLogger(__name__)


class TwilioPhoneTool:
    """Tool responsible for handling Twilio phone calls with AI conversation."""

    def __init__(
        self,
        speech_tool: Optional["SpeechToTextTool"] = None,
        tts_tool: Optional["TextToSpeechTool"] = None,
        conversation_tool: Optional["ConversationalResponseTool"] = None,
    ) -> None:
        """Initialize TwilioPhoneTool with existing voice agent tools."""
        if speech_tool is None:
            from tools.understanding.speech_to_text import SpeechToTextTool
            self.speech_tool = SpeechToTextTool()
        else:
            self.speech_tool = speech_tool

        if tts_tool is None:
            from tools.response.text_to_speech import TextToSpeechTool
            self.tts_tool = TextToSpeechTool()
        else:
            self.tts_tool = tts_tool

        if conversation_tool is None:
            from tools.response.conversation import ConversationalResponseTool
            self.conversation_tool = ConversationalResponseTool()
        else:
            self.conversation_tool = conversation_tool

        # Track active calls: {call_sid: session_id}
        self.active_calls: Dict[str, str] = {}
        # Track session data: {session_id: session_data}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        # Audio buffers for each call: {call_sid: [audio_chunks]}
        self.audio_buffers: Dict[str, list] = {}
        # Track if AI is speaking: {call_sid: bool} - prevents feedback loop
        self.is_speaking: Dict[str, bool] = {}

        logger.info("TwilioPhoneTool initialized")

    async def handle_incoming_call(self, call_data: Dict[str, Any]) -> str:
        """
        Handle incoming call webhook from Twilio.
        
        Args:
            call_data: Dictionary containing call information from Twilio webhook
                - CallSid: Unique call identifier
                - From: Caller's phone number
                - To: Called number
                - CallStatus: Call status
        
        Returns:
            TwiML XML string to instruct Twilio on how to handle the call
        """
        call_sid = call_data.get("CallSid")
        from_number = call_data.get("From", "unknown")
        
        if not call_sid:
            logger.error("No CallSid in incoming call webhook")
            return self._create_error_twiml("Invalid call data")

        logger.info(f"Incoming call: {call_sid} from {from_number}")

        try:
            # Create conversation session
            session_data = self.conversation_tool.create_session(
                customer_id=f"phone_{from_number}",
                persona=None  # Use default persona
            )
            
            session_id = session_data.get("session_id", call_sid)
            
            # Store call mapping and session
            self.active_calls[call_sid] = session_id
            self.session_data[session_id] = session_data
            self.audio_buffers[call_sid] = []

            # Create TwiML response to start Media Stream
            response = VoiceResponse()
            
            # Start Media Stream - this enables real-time bidirectional audio
            # Include CallSid as parameter so we can map it to the session
            # Use wss:// for WebSocket (required for Media Stream)
            stream_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/stream?CallSid={call_sid}"
            # Ensure WebSocket URL uses wss:// protocol
            if stream_url.startswith("https://"):
                stream_url = stream_url.replace("https://", "wss://", 1)
            elif stream_url.startswith("http://"):
                stream_url = stream_url.replace("http://", "ws://", 1)
            
            response.start().stream(url=stream_url)

            # Generate initial greeting
            greeting_result = await self.conversation_tool.generate_response(
                session_data,
                "",  # Empty input for initial greeting
                persona=None
            )
            
            greeting_text = greeting_result.get("response", "Hello! How can I help you today?")
            
            # Say initial greeting while Media Stream connects
            response.say(greeting_text, voice="alice")

            twiml = str(response)
            logger.info(f"Call {call_sid} connected, session {session_id} created")
            return twiml

        except Exception as e:
            logger.error(f"Error handling incoming call {call_sid}: {e}")
            return self._create_error_twiml(str(e))

    async def handle_media_stream(self, websocket: WebSocket, call_sid: Optional[str] = None):
        """
        Handle Media Stream WebSocket connection from Twilio.
        
        This processes real-time bidirectional audio:
        - Incoming: Twilio sends μ-law PCM audio → Convert to WAV → STT → Conversation → TTS → Convert to μ-law → Send back
        
        Args:
            websocket: WebSocket connection from Twilio Media Stream
            call_sid: Twilio call identifier (may be in query params or in stream messages)
        """
        await websocket.accept()
        logger.info("Media Stream WebSocket connection accepted")
        
        # CallSid may come from query params or from stream messages
        # Don't close connection if not provided - wait for "start" event
        session_id = None
        session_data = {}
        audio_buffer = []

        try:
            # Send initial connection message
            await websocket.send_text(json.dumps({
                "event": "connected",
                "protocol": "Call",
                "version": "1.0.0"
            }))

            # Process incoming messages
            while True:
                try:
                    # Receive message from Twilio
                    message = await websocket.receive_text()
                    
                    if not message:
                        continue

                    # Parse Media Stream message
                    data = json.loads(message)
                    event_type = data.get("event")

                    if event_type == "start":
                        # Extract CallSid from start event (Twilio sends it here)
                        start_data = data.get("start", {})
                        stream_call_sid = start_data.get("callSid") or data.get("callSid") or call_sid
                        
                        if stream_call_sid and stream_call_sid != "unknown":
                            call_sid = stream_call_sid
                            logger.info(f"Media Stream started for call {call_sid}")
                            
                            # Get or create session
                            session_id = self.active_calls.get(call_sid)
                            if not session_id:
                                logger.warning(f"No session found for call {call_sid}, creating new session")
                                # Create session on the fly if needed
                                from_number = start_data.get("callerNumber", "unknown")
                                session_data = self.conversation_tool.create_session(
                                    customer_id=f"phone_{from_number}",
                                    persona=None
                                )
                                session_id = session_data.get("session_id", call_sid)
                                self.active_calls[call_sid] = session_id
                                self.session_data[session_id] = session_data
                                self.audio_buffers[call_sid] = []
                            else:
                                session_data = self.session_data.get(session_id, {})
                            
                            audio_buffer = self.audio_buffers.get(call_sid, [])
                        else:
                            logger.error("No CallSid found in start event")
                    
                    elif event_type == "media":
                        if not call_sid:
                            logger.warning("Received media before start event, skipping")
                            continue
                        
                        if not session_id:
                            logger.warning("Received media before session initialized, skipping")
                            continue
                        
                        # IMPORTANT: Skip processing if AI is currently speaking
                        # This prevents the AI from hearing its own voice (feedback loop)
                        if self.is_speaking.get(call_sid, False):
                            # AI is speaking, ignore incoming audio to prevent feedback
                            continue
                        
                        # Incoming audio data
                        media_payload = data.get("media", {})
                        audio_base64 = media_payload.get("payload")
                        
                        if audio_base64:
                            # Decode μ-law PCM audio
                            audio_bytes = base64.b64decode(audio_base64)
                            
                            # Add to buffer
                            audio_buffer.append(audio_bytes)
                            
                            # Process when buffer reaches threshold (~2 seconds of audio)
                            if len(audio_buffer) >= 16:  # ~2 seconds at 8000Hz
                                # Combine audio chunks
                                combined_audio = b''.join(audio_buffer)
                                audio_buffer.clear()
                                
                                # Process audio asynchronously
                                asyncio.create_task(self._process_phone_audio(
                                    combined_audio, session_id, call_sid, websocket
                                ))

                    elif event_type == "stop":
                        logger.info(f"Media Stream stopped for call {call_sid}")
                        break

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in Media Stream message: {message}")
                    continue
                except WebSocketDisconnect:
                    logger.info(f"Media Stream disconnected for call {call_sid}")
                    break
                except Exception as e:
                    logger.error(f"Error processing Media Stream message: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in Media Stream handler for call {call_sid or 'unknown'}: {e}")
        finally:
            # Cleanup
            if call_sid:
                self._cleanup_call(call_sid)
            try:
                await websocket.close()
            except:
                pass

    async def _process_phone_audio(
        self,
        audio_data: bytes,
        session_id: str,
        call_sid: str,
        websocket: WebSocket
    ):
        """
        Process audio from phone call using existing voice agent tools.
        
        Pipeline:
        1. Convert Twilio audio (μ-law PCM) to WAV
        2. Use SpeechToTextTool to transcribe
        3. Use ConversationalResponseTool to generate response
        4. Use TextToSpeechTool to generate audio
        5. Convert audio back to Twilio format
        6. Send back through Media Stream
        """
        try:
            # Step 1: Convert Twilio audio to WAV format
            wav_audio = twilio_to_wav(audio_data, sample_rate=8000)
            
            # Step 2: Speech-to-Text
            stt_result = await self.speech_tool.transcribe(wav_audio, "wav")
            
            if not stt_result.get("success"):
                logger.warning(f"STT failed for call {call_sid}: {stt_result.get('error')}")
                return
            
            user_text = stt_result.get("text", "").strip()
            
            if not user_text:
                logger.debug("Empty transcription, skipping")
                return
            
            logger.info(f"Call {call_sid}: User said: {user_text[:100]}")
            
            # Step 3: Get conversation response
            session_data = self.session_data.get(session_id, {})
            conversation_result = await self.conversation_tool.generate_response(
                session_data,
                user_text,
                persona=None
            )
            
            # Update session data
            self.session_data[session_id] = conversation_result.get("session_data", session_data)
            
            agent_text = conversation_result.get("response", "")
            logger.info(f"Call {call_sid}: Agent responding: {agent_text[:100]}")
            
            # Step 4: Text-to-Speech
            tts_result = await self.tts_tool.synthesize(
                agent_text,
                voice="alloy",  # Default voice
                persona=None
            )
            
            if not tts_result.get("success"):
                logger.error(f"TTS failed for call {call_sid}: {tts_result.get('error')}")
                return
            
            # Get audio bytes
            audio_bytes = tts_result.get("audio_bytes")
            if not audio_bytes:
                # Try to decode from base64 if available
                audio_base64 = tts_result.get("audio_base64")
                if audio_base64:
                    audio_bytes = base64.b64decode(audio_base64)
                else:
                    logger.error("No audio data in TTS result")
                    return
            
            # Step 5: Convert to Twilio format (μ-law PCM, 8000Hz)
            twilio_audio = wav_to_twilio(audio_bytes, sample_rate=16000)
            
            # Step 6: Send audio back through Media Stream
            # Mark as speaking to prevent feedback loop
            self.is_speaking[call_sid] = True
            
            # Send in chunks (160 bytes per chunk = 20ms at 8000Hz)
            chunk_size = 160
            for i in range(0, len(twilio_audio), chunk_size):
                chunk = twilio_audio[i:i + chunk_size]
                audio_payload = base64.b64encode(chunk).decode('utf-8')
                
                media_message = {
                    "event": "media",
                    "streamSid": call_sid,
                    "media": {
                        "payload": audio_payload
                    }
                }
                
                try:
                    await websocket.send_text(json.dumps(media_message))
                except Exception as e:
                    logger.error(f"Error sending audio chunk: {e}")
                    break
            
            # Wait a short delay after sending audio before accepting input again
            # This prevents capturing the tail end of AI's speech
            await asyncio.sleep(0.5)  # 500ms buffer
            
            # Mark as done speaking
            self.is_speaking[call_sid] = False
            logger.debug(f"Call {call_sid}: Finished speaking, ready for user input")

        except Exception as e:
            logger.error(f"Error processing phone audio for call {call_sid}: {e}")
            # Reset speaking flag on error
            self.is_speaking[call_sid] = False

    async def handle_call_status(self, status_data: Dict[str, Any]):
        """
        Handle call status updates from Twilio.
        
        Args:
            status_data: Dictionary containing call status information
                - CallSid: Call identifier
                - CallStatus: Status (ringing, answered, completed, failed, etc.)
        """
        call_sid = status_data.get("CallSid")
        status = status_data.get("CallStatus", "unknown")
        
        logger.info(f"Call {call_sid} status: {status}")
        
        if status in ["completed", "failed", "busy", "no-answer"]:
            # Clean up call resources
            self._cleanup_call(call_sid)

    def _cleanup_call(self, call_sid: str):
        """Clean up resources for a call."""
        if call_sid in self.active_calls:
            session_id = self.active_calls[call_sid]
            del self.active_calls[call_sid]
            
            if session_id in self.session_data:
                # Optionally keep session data for history
                pass
            
            if call_sid in self.audio_buffers:
                del self.audio_buffers[call_sid]
            
            if call_sid in self.is_speaking:
                del self.is_speaking[call_sid]
            
            logger.info(f"Cleaned up resources for call {call_sid}")

    def _create_error_twiml(self, error_message: str) -> str:
        """Create error TwiML response."""
        response = VoiceResponse()
        response.say(f"I'm sorry, an error occurred: {error_message}", voice="alice")
        response.hangup()
        return str(response)

