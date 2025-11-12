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
        # Track agent configs for each call: {call_sid: agent_config}
        self.call_agent_configs: Dict[str, Dict[str, Any]] = {}

        logger.info("TwilioPhoneTool initialized")

    async def handle_incoming_call(self, call_data: Dict[str, Any]) -> str:
        """
        Handle incoming call webhook from Twilio.
        
        Args:
            call_data: Dictionary containing call information from Twilio webhook
                - CallSid: Unique call identifier
                - From: Caller's phone number
                - To: Called number (phone number being called)
                - CallStatus: Call status
        
        Returns:
            TwiML XML string to instruct Twilio on how to handle the call
        """
        call_sid = call_data.get("CallSid")
        from_number = call_data.get("From", "unknown")
        to_number = call_data.get("To", "unknown")
        
        if not call_sid:
            logger.error("No CallSid in incoming call webhook")
            return self._create_error_twiml("Invalid call data")

        logger.info(f"Incoming call: {call_sid} from {from_number} to {to_number}")

        try:
            # Load active agent configuration for this phone number
            agent_config = await self._load_agent_config(to_number)
            
            if not agent_config:
                logger.warning(f"❌ No active agent found for phone number {to_number}")
                # Return error message saying number does not exist
                response = VoiceResponse()
                response.say("Sorry, this number does not exist. Please check the number and try again. Goodbye.", voice="alice")
                response.hangup()
                logger.info(f"Call {call_sid} rejected: Number {to_number} not found in agents collection")
                return str(response)
            
            logger.info(f"✅ Using agent config for {to_number}: {agent_config.get('name', 'Unknown')}")
            logger.info(f"   STT: {agent_config.get('sttModel')}, TTS: {agent_config.get('ttsModel')} ({agent_config.get('ttsVoice')}), LLM: {agent_config.get('inferenceModel')}")
            
            # Store agent config for this call
            self.call_agent_configs[call_sid] = agent_config
            
            # Create conversation session
            session_data = self.conversation_tool.create_session(
                customer_id=f"phone_{from_number}",
                persona=None
            )
            # Set system prompt in session data if agent config has one
            if agent_config.get("systemPrompt"):
                session_data["systemPrompt"] = agent_config.get("systemPrompt")
            
            session_id = session_data.get("session_id", call_sid)
            
            # Store call mapping and session
            self.active_calls[call_sid] = session_id
            self.session_data[session_id] = session_data
            self.audio_buffers[call_sid] = []

            # Use simple TwiML approach (More reliable than Media Stream)
            # Media Stream has connectivity issues on some Twilio accounts
            response = VoiceResponse()
            
            # Use agent's greeting or default
            greeting = agent_config.get("greeting", "Hello! How can I help you today?")
            response.say(greeting, voice="alice")
            
            # Record the caller's message
            record_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/recording?CallSid={call_sid}"
            response.record(
                action=record_url,
                method="POST",
                max_speech_time=10,  # Max 10 seconds of speech
                speech_timeout="auto"
            )

            twiml = str(response)
            logger.info(f"✅ Call {call_sid} TwiML Response Generated:")
            logger.info(f"   TwiML:\n{twiml}")
            logger.info(f"✅ Call {call_sid} connected, session {session_id} created. Playing greeting and recording input...")
            return twiml

        except Exception as e:
            logger.error(f"Error handling incoming call {call_sid}: {e}", exc_info=True)
            return self._create_error_twiml(str(e))
    
    async def _load_agent_config(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Load active agent configuration for a phone number from MongoDB.
        
        Args:
            phone_number: Phone number to look up (e.g., "+15551234567" or "5551234567")
        
        Returns:
            Agent configuration dict or None if not found
        """
        try:
            from databases.mongodb_agent_store import MongoDBAgentStore
            
            agent_store = MongoDBAgentStore()
            
            # Normalize phone number (remove +1, spaces, dashes, etc.)
            normalized_phone = phone_number.replace("+1", "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
            
            # Try to find active agent with this phone number
            agents = await agent_store.list_agents(active_only=True)
            
            for agent in agents:
                agent_phone = agent.get("phoneNumber", "").replace("+1", "").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                if agent_phone == normalized_phone:
                    logger.info(f"Found active agent for {phone_number}: {agent.get('name')}")
                    return agent
            
            logger.warning(f"No active agent found for phone number {phone_number}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading agent config for {phone_number}: {e}", exc_info=True)
            return None

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
        logger.info(f"✅ Media Stream WebSocket connection ACCEPTED. CallSid from params: {call_sid}")
        
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
                                self.is_speaking[call_sid] = False
                            else:
                                session_data = self.session_data.get(session_id, {})
                            
                            audio_buffer = self.audio_buffers.get(call_sid, [])
                            
                            # Check if we need to send initial greeting
                            if audio_buffer and audio_buffer[0] == b'__SEND_GREETING__':
                                audio_buffer.clear()
                                logger.info(f"Call {call_sid}: Sending initial greeting through Media Stream")
                                # Send greeting asynchronously
                                asyncio.create_task(self._send_audio_response(
                                    "Hello! How can I help you today?",
                                    call_sid,
                                    websocket
                                ))
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
                            
                            # Process when buffer reaches threshold (~1 second of audio for faster response)
                            # Reduced from 16 to 8 chunks for more responsive processing
                            if len(audio_buffer) >= 8:  # ~1 second at 8000Hz (faster processing)
                                # Combine audio chunks
                                combined_audio = b''.join(audio_buffer)
                                audio_buffer.clear()
                                
                                logger.debug(f"Call {call_sid}: Processing audio buffer ({len(combined_audio)} bytes)")
                                
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

    async def _send_audio_response(
        self,
        text: str,
        call_sid: str,
        websocket: WebSocket
    ):
        """
        Helper method to convert text to speech and send through Media Stream.
        
        Args:
            text: Text to convert to speech
            call_sid: Call identifier
            websocket: WebSocket connection for Media Stream
        """
        try:
            if not text or not text.strip():
                logger.warning(f"Empty text provided for TTS, call {call_sid}")
                return
            
            # Text-to-Speech
            tts_result = await self.tts_tool.synthesize(
                text,
                voice="alloy",  # Default voice
                persona=None,
                parallel=False  # Disable parallel for phone calls (shorter responses)
            )
            
            if not tts_result.get("success"):
                error_msg = tts_result.get('error', 'Unknown error')
                logger.error(f"TTS failed for call {call_sid}: {error_msg}")
                # Send a fallback message
                fallback_text = "I'm sorry, I'm having trouble speaking right now. Please try again."
                # Try one more time with fallback
                fallback_tts = await self.tts_tool.synthesize(
                    fallback_text,
                    voice="alloy",
                    persona=None,
                    parallel=False
                )
                if not fallback_tts.get("success"):
                    logger.error(f"Fallback TTS also failed for call {call_sid}")
                    return
                tts_result = fallback_tts
            
            # Get audio bytes
            audio_bytes = tts_result.get("audio_bytes")
            if not audio_bytes:
                # Try to decode from base64 if available
                audio_base64 = tts_result.get("audio_base64")
                if audio_base64:
                    audio_bytes = base64.b64decode(audio_base64)
                else:
                    logger.error(f"No audio data in TTS result for call {call_sid}")
                    return
            
            # Convert to Twilio format (μ-law PCM, 8000Hz)
            twilio_audio = wav_to_twilio(audio_bytes, sample_rate=16000)
            
            # Send audio back through Media Stream
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
                    logger.error(f"Error sending audio chunk for call {call_sid}: {e}")
                    break
            
            # Wait a short delay after sending audio before accepting input again
            # This prevents capturing the tail end of AI's speech
            await asyncio.sleep(0.5)  # 500ms buffer
            
            # Mark as done speaking
            self.is_speaking[call_sid] = False
            logger.debug(f"Call {call_sid}: Finished speaking, ready for user input")
            
        except Exception as e:
            logger.error(f"Error in _send_audio_response for call {call_sid}: {e}")
            # Reset speaking flag on error
            self.is_speaking[call_sid] = False

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
            try:
                wav_audio = twilio_to_wav(audio_data, sample_rate=8000)
                logger.debug(f"Call {call_sid}: Converted {len(audio_data)} bytes to {len(wav_audio)} bytes WAV")
            except Exception as e:
                logger.error(f"Call {call_sid}: Audio conversion failed: {e}")
                # Send helpful error message
                await self._send_audio_response(
                    "I'm sorry, there was an audio processing error. Please try speaking again.",
                    call_sid,
                    websocket
                )
                return
            
            # Step 2: Speech-to-Text
            logger.debug(f"Call {call_sid}: Sending audio to STT ({len(wav_audio)} bytes)")
            stt_result = await self.speech_tool.transcribe(wav_audio, "wav")
            
            if not stt_result.get("success"):
                error_msg = stt_result.get('error', 'Unknown error')
                logger.warning(f"STT failed for call {call_sid}: {error_msg}")
                # Send a helpful response instead of just returning
                fallback_text = "I'm sorry, I couldn't hear you clearly. Could you please speak a bit louder or repeat that?"
                await self._send_audio_response(fallback_text, call_sid, websocket)
                return
            
            user_text = stt_result.get("text", "").strip()
            
            if not user_text:
                logger.debug("Empty transcription, skipping - likely silence or background noise")
                # Don't respond to silence/noise - just return silently
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
            
            # Step 4: Send audio response
            await self._send_audio_response(agent_text, call_sid, websocket)

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
            
            if call_sid in self.call_agent_configs:
                del self.call_agent_configs[call_sid]
            
            logger.info(f"Cleaned up resources for call {call_sid}")

    def _create_error_twiml(self, error_message: str) -> str:
        """Create error TwiML response."""
        response = VoiceResponse()
        response.say(f"I'm sorry, an error occurred: {error_message}", voice="alice")
        response.hangup()
        return str(response)

