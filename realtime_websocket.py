"""
Real-time Voice Agent WebSocket Handler
This module provides real-time voice processing using WebSockets and streaming audio.
"""

import asyncio
import json
import base64
import logging
import struct
from typing import Dict, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import io

from voice_processor import VoiceProcessor
from conversation_manager import ConversationManager
from config import MAX_AUDIO_FILE_SIZE, ALLOWED_AUDIO_FORMATS
from tools.provider_factory import get_stt_tool, get_tts_tool
from databases.mongodb_ai_chat_store import MongoDBChatStore

logger = logging.getLogger(__name__)

# ============================================================================
# NOISE FILTERING (same patterns as TwilioStreamHandler)
# ============================================================================
import re

# Noise phrases that STT often produces from silence/background noise
NOISE_PHRASES = {
    "silence", "click", "clear speech", "phone call audio",
    "phone call audio transcription", "phone call", "transcription",
    "uh", "um", "hmm", "ah", "oh", "huh", "eh", "mm", "mhm",
    ".", "..", "...", "", " ", "you", "the", "a", "i", "it", "is", "to"
}

# Valid short responses that should NOT be filtered
VALID_SHORT_RESPONSES = {"ok", "no", "hi", "go", "ya", "ye", "by", "bye", "yes", "hey"}

# Minimum transcript length
MIN_TRANSCRIPT_LENGTH = 3

# Unclear/incomplete question phrases - use previous context
UNCLEAR_PHRASES = {
    "what", "huh", "sorry", "pardon", "come again", "say again", 
    "repeat", "say that again", "what was that", "excuse me",
    "i didnt catch", "didn't catch", "didnt hear", "didn't hear"
}

def _is_unclear_question(text: str) -> bool:
    """Check if user's question is unclear/incomplete and needs context."""
    if not text:
        return False
    clean = text.strip().lower().rstrip("?.,!")
    # Direct match with unclear phrases
    if clean in UNCLEAR_PHRASES:
        return True
    # Check for partial matches
    for phrase in UNCLEAR_PHRASES:
        if phrase in clean and len(clean) < 20:  # Short text containing unclear phrase
            return True
    # Very short text (less than 5 chars) that's not a valid response
    if len(clean) < 5 and clean not in VALID_SHORT_RESPONSES:
        return True
    return False

def _is_valid_transcript(text: str) -> bool:
    """Validate that transcript is meaningful speech, not noise.
    Returns False for single chars, noise words, parenthetical sounds, and very short text."""
    if not text:
        return False
    
    text_clean = text.strip().lower()
    
    # Filter parenthetical sound/action descriptions (e.g., "(car engine starts)", "(soft music)")
    # These are common STT artifacts from background noise
    if re.match(r'^\s*\([^)]+\)\s*$', text_clean):
        logger.info(f"🔇 Rejecting parenthetical sound description: '{text}'")
        return False
    
    # Also filter if it contains parenthetical content describing sounds/actions
    sound_pattern = r'\([^)]*(?:music|engine|sound|noise|beep|ring|click|door|car|phone|background|silence|static|breathing|cough|sneeze|laugh|sigh|hum|whisper|murmur|rustl|shuffl|tap|knock|buzz)[^)]*\)'
    if re.search(sound_pattern, text_clean, re.IGNORECASE):
        logger.info(f"🔇 Rejecting transcript with sound description: '{text}'")
        return False
    
    # Strip punctuation for more accurate noise detection
    # This ensures "Oh." is treated the same as "oh"
    text_no_punct = re.sub(r'[^\w\s]', '', text_clean).strip()
    
    # Allow valid short responses even if < MIN_TRANSCRIPT_LENGTH
    if text_no_punct in VALID_SHORT_RESPONSES:
        return True
    
    # Too short (check length WITHOUT punctuation)
    if len(text_no_punct) < MIN_TRANSCRIPT_LENGTH:
        logger.info(f"🔇 Rejecting short transcript: '{text}' -> '{text_no_punct}' ({len(text_no_punct)} chars)")
        return False
    
    # Known noise phrases (check WITHOUT punctuation)
    if text_no_punct in NOISE_PHRASES:
        logger.info(f"🔇 Rejecting noise phrase: '{text}'")
        return False
    
    # Single-word noise check
    words = text_no_punct.split()
    if len(words) == 1 and text_no_punct in NOISE_PHRASES:
        logger.info(f"🔇 Rejecting single noise word: '{text}'")
        return False
    
    return True

# Stop phrases that trigger session end (ported from TwilioStreamHandler)
CALL_END_PHRASES = [
    "goodbye", "bye-bye", "bye bye", "good bye", "bye.",
    "take care", "have a great day", "have a good day",
    "talk to you later", "speak to you later", "have a nice day",
    "thanks for calling", "thank you for calling"
]

class RealTimeVoiceAgent:
    """Real-time voice agent for WebSocket connections
    
    Enhanced with:
    - Query sequencing (latest query wins)
    - Interrupt handling (cancel in-flight processing)
    - Streaming LLM->TTS pipeline (low latency)
    - Stop condition detection (farewell phrases)
    """
    
    def __init__(self):
        # Default (fallback) VoiceProcessor with OpenAI
        self.default_voice_processor = VoiceProcessor()
        self.conversation_manager = ConversationManager()
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.audio_buffers: Dict[str, List[bytes]] = {}
        
        # Query sequencing and interrupt handling (per-session)
        self.query_sequences: Dict[str, int] = {}           # Track latest query ID per session
        self.processing_tasks: Dict[str, asyncio.Task] = {} # Track active processing task per session
        self.ai_speaking: Dict[str, bool] = {}              # Track if AI is currently speaking per session
        
        # Silence-based processing (per-session)
        # Wait for 2 seconds of silence after user stops speaking before responding
        self.chunk_count: Dict[str, int] = {}               # Count chunks received
        self.last_chunk_time: Dict[str, float] = {}         # Track when last chunk was received
        self.silence_check_tasks: Dict[str, asyncio.Task] = {}  # Background tasks checking for silence
        self.SILENCE_WAIT_SECONDS = 2.0                     # Wait 2 seconds of silence before responding
        self.MAX_BUFFER_BYTES = 100000                      # Max buffer before forcing process (safety limit)
        
        # Context tracking for unclear questions
        self.last_user_question: Dict[str, str] = {}        # Last meaningful question per session
        self.last_question_answered: Dict[str, bool] = {}   # Whether last question was answered
        
        # Inactivity timeout tracking
        self.last_user_speech_time: Dict[str, float] = {}   # When user last spoke
        self.inactivity_reminder_count: Dict[str, int] = {} # Reminders sent (max 3)
        self.inactivity_check_tasks: Dict[str, asyncio.Task] = {}  # Background inactivity checker
        self.INACTIVITY_REMINDER_INTERVAL = 10.0            # Remind every 10 seconds
        self.MAX_INACTIVITY_REMINDERS = 3                   # Max reminders before auto-end
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.audio_buffers[session_id] = []
        
        # Initialize session data
        self.session_data[session_id] = self.conversation_manager.create_session()
        
        # Initialize query sequencing and interrupt state
        self.query_sequences[session_id] = 0
        self.processing_tasks[session_id] = None
        self.ai_speaking[session_id] = False
        
        # Initialize chunk counting and silence detection state
        self.chunk_count[session_id] = 0
        self.last_chunk_time[session_id] = 0.0
        self.silence_check_tasks[session_id] = None
        
        # Initialize context tracking
        self.last_user_question[session_id] = ""
        self.last_question_answered[session_id] = True
        
        # Initialize inactivity tracking
        import time
        self.last_user_speech_time[session_id] = time.time()
        self.inactivity_reminder_count[session_id] = 0
        self.inactivity_check_tasks[session_id] = None
        
        logger.info(f"WebSocket connected for session: {session_id}")
        
        # Send welcome message
        await self.send_message(session_id, {
            "type": "connection_established",
            "message": "Connected to real-time voice agent",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def connect_with_config(
        self,
        websocket: WebSocket,
        session_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """Accept WebSocket connection with custom AI model configuration.
        
        This is an extension for AI Chat feature. Original connect() is unchanged.
        
        Args:
            websocket: FastAPI WebSocket connection
            session_id: Unique session identifier
            config: Optional AI configuration with keys:
                - stt_model: Speech-to-text model (e.g., "whisper-1")
                - tts_model: Text-to-speech model (e.g., "tts-1")
                - tts_voice: TTS voice (e.g., "alloy")
                - inference_model: LLM model (e.g., "gpt-4o-mini")
                - provider: "openai" or "elevenlabs"
                - system_prompt: Optional custom system prompt
        """
        # Use base connect logic
        await self.connect(websocket, session_id)
        
        # Store config in session data and create per-session VoiceProcessor
        if config:
            self.session_data[session_id]["config"] = config
            
            # Create per-session VoiceProcessor based on config models (supports ElevenLabs)
            stt_model = config.get("stt_model", "whisper-1")
            tts_model = config.get("tts_model", "tts-1")
            
            stt_tool = get_stt_tool(stt_model)
            tts_tool = get_tts_tool(tts_model)
            
            self.session_data[session_id]["voice_processor"] = VoiceProcessor(
                speech_tool=stt_tool,
                tts_tool=tts_tool
            )
            
            provider = config.get('provider', 'openai')
            logger.info(f"AI Chat session {session_id} configured: provider={provider}, stt={stt_model}, tts={tts_model}")
            
            # Start inactivity checker for AI Chat sessions
            self.inactivity_check_tasks[session_id] = asyncio.create_task(
                self._check_inactivity(session_id)
            )
            logger.info(f"⏰ Started inactivity checker for session {session_id}")
    
    def get_session_config(self, session_id: str) -> Dict[str, Any]:
        """Get AI configuration for a session.
        
        Returns config dict or empty dict if not set.
        """
        session = self.session_data.get(session_id, {})
        return session.get("config", {})
    
    async def disconnect(self, session_id: str):
        """Handle WebSocket disconnection"""
        # Cancel any active processing task
        if session_id in self.processing_tasks:
            task = self.processing_tasks[session_id]
            if task and not task.done():
                task.cancel()
                logger.info(f"Cancelled active processing task for session {session_id}")
            del self.processing_tasks[session_id]
        
        # Cancel any silence check task
        if session_id in self.silence_check_tasks:
            task = self.silence_check_tasks[session_id]
            if task and not task.done():
                task.cancel()
            del self.silence_check_tasks[session_id]
        
        # Cancel any inactivity check task
        if session_id in self.inactivity_check_tasks:
            task = self.inactivity_check_tasks[session_id]
            if task and not task.done():
                task.cancel()
            del self.inactivity_check_tasks[session_id]
        
        # Clean up all session state
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        if session_id in self.audio_buffers:
            del self.audio_buffers[session_id]
        if session_id in self.query_sequences:
            del self.query_sequences[session_id]
        if session_id in self.ai_speaking:
            del self.ai_speaking[session_id]
        if session_id in self.chunk_count:
            del self.chunk_count[session_id]
        if session_id in self.last_chunk_time:
            del self.last_chunk_time[session_id]
        if session_id in self.last_user_speech_time:
            del self.last_user_speech_time[session_id]
        if session_id in self.inactivity_reminder_count:
            del self.inactivity_reminder_count[session_id]
        
        logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {str(e)}")
                await self.disconnect(session_id)
    
    def _should_end_session(self, text: str) -> bool:
        """Check if AI response contains farewell phrases indicating session should end.
        
        Ported from TwilioStreamHandler._should_end_call for consistency.
        """
        text_lower = text.lower()
        for phrase in CALL_END_PHRASES:
            if phrase in text_lower:
                return True
        return False
    
    async def _check_inactivity(self, session_id: str):
        """Background task to check for user inactivity and send reminders.
        
        - After 10s of silence: Send reminder #1
        - After 20s of silence: Send reminder #2
        - After 30s of silence: Send reminder #3 + auto-end
        """
        import time
        
        REMINDER_MESSAGES = [
            "Are you still there?",
            "I'm still here if you need anything.",
            "It seems you're busy. Goodbye for now!"
        ]
        
        try:
            while True:
                await asyncio.sleep(2)  # Check every 2 seconds
                
                # Check if session still exists
                if session_id not in self.active_connections:
                    logger.debug(f"Session {session_id} disconnected, stopping inactivity check")
                    return
                
                # Skip check if AI is speaking
                if self.ai_speaking.get(session_id, False):
                    continue
                
                # Calculate time since last speech
                last_speech = self.last_user_speech_time.get(session_id, time.time())
                elapsed = time.time() - last_speech
                reminder_count = self.inactivity_reminder_count.get(session_id, 0)
                
                # Determine if we should send a reminder
                expected_reminders = int(elapsed // self.INACTIVITY_REMINDER_INTERVAL)
                
                if expected_reminders > reminder_count and reminder_count < self.MAX_INACTIVITY_REMINDERS:
                    # Time to send a reminder
                    reminder_index = min(reminder_count, len(REMINDER_MESSAGES) - 1)
                    reminder_text = REMINDER_MESSAGES[reminder_index]
                    
                    logger.info(f"⏰ Inactivity reminder #{reminder_count + 1} for session {session_id}: '{reminder_text}'")
                    
                    # Get voice processor for TTS
                    session_data = self.session_data.get(session_id, {})
                    voice_processor = session_data.get("voice_processor", self.default_voice_processor)
                    config = session_data.get("config", {})
                    tts_voice = config.get("tts_voice", "alloy")
                    
                    # Generate and send reminder audio
                    try:
                        tts_result = await voice_processor.generate_voice_response(reminder_text, tts_voice)
                        
                        if tts_result.get("success"):
                            await self.send_message(session_id, {
                                "type": "inactivity_reminder",
                                "text": reminder_text,
                                "audio_base64": tts_result.get("audio_base64"),
                                "reminder_number": reminder_count + 1,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                    except Exception as e:
                        logger.warning(f"Failed to generate reminder audio: {e}")
                    
                    # Update reminder count
                    self.inactivity_reminder_count[session_id] = reminder_count + 1
                    
                    # Check if this was the final reminder
                    if reminder_count + 1 >= self.MAX_INACTIVITY_REMINDERS:
                        logger.info(f"⏰ Max inactivity reminders reached for session {session_id}, ending session")
                        await self.send_message(session_id, {
                            "type": "inactivity_end",
                            "message": "Session ended due to inactivity",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        return
                        
        except asyncio.CancelledError:
            logger.debug(f"Inactivity check task cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Error in inactivity check for {session_id}: {e}")
    
    async def handle_interrupt(self, session_id: str):
        """Handle user interrupt - cancel current processing and notify frontend.
        
        This is called when user speaks while AI is responding (barge-in).
        Ported from TwilioStreamHandler interrupt detection patterns.
        """
        # Cancel active processing task if running
        if session_id in self.processing_tasks:
            task = self.processing_tasks[session_id]
            if task and not task.done():
                task.cancel()
                logger.info(f"🛑 Cancelled processing for session {session_id} due to interrupt")
        
        # Increment query sequence to invalidate any in-flight responses
        self.query_sequences[session_id] = self.query_sequences.get(session_id, 0) + 1
        logger.info(f"🔄 Query sequence for {session_id} incremented to {self.query_sequences[session_id]}")
        
        # Mark AI as not speaking
        self.ai_speaking[session_id] = False
        
        # Notify frontend to clear audio queue and stop playback
        await self.send_message(session_id, {
            "type": "interrupt_clear",
            "message": "User interrupted, clearing audio queue",
            "query_id": self.query_sequences[session_id],
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _generate_clauses_from_stream(self, sentence_stream):
        """Re-yield LLM sentences as smaller clauses for faster first-audio.
        
        Breaks sentences on commas, colons, semicolons for lower latency.
        Minimum clause size prevents too-short TTS calls.
        """
        MIN_CLAUSE_SIZE = 15  # Minimum chars before yielding
        
        async for sentence in sentence_stream:
            # Check for clause boundaries within the sentence
            buffer = ""
            for char in sentence:
                buffer += char
                # Yield on clause boundaries if buffer is long enough
                if char in ',;:' and len(buffer.strip()) >= MIN_CLAUSE_SIZE:
                    clause = buffer.strip()
                    buffer = ""
                    if clause:
                        yield clause
            
            # Yield any remaining text
            if buffer.strip():
                yield buffer.strip()
    
    async def _check_silence_and_process(self, session_id: str, audio_format: str):
        """Background task to check for silence and trigger processing.
        
        Waits for SILENCE_WAIT_SECONDS of no new audio chunks before triggering STT.
        """
        try:
            while True:
                await asyncio.sleep(0.5)  # Check every 500ms
                
                # Check if session still exists
                if session_id not in self.active_connections:
                    logger.debug(f"Session {session_id} disconnected, stopping silence check")
                    return
                
                # Check if we have audio to process
                if session_id not in self.audio_buffers or not self.audio_buffers[session_id]:
                    continue
                
                # Calculate time since last chunk
                last_time = self.last_chunk_time.get(session_id, 0)
                if last_time == 0:
                    continue
                
                import time
                elapsed = time.time() - last_time
                
                # If enough silence has passed, trigger processing
                if elapsed >= self.SILENCE_WAIT_SECONDS:
                    buffer_size = sum(len(chunk) for chunk in self.audio_buffers[session_id])
                    if buffer_size > 0:
                        logger.info(f"🔇 {self.SILENCE_WAIT_SECONDS}s silence detected, triggering STT ({buffer_size} bytes)")
                        await self._trigger_audio_processing(session_id, audio_format)
                        return  # Task complete
                        
        except asyncio.CancelledError:
            logger.debug(f"Silence check task cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Error in silence check for {session_id}: {e}")
    
    async def _trigger_audio_processing(self, session_id: str, audio_format: str):
        """Trigger audio processing with current buffer."""
        try:
            # Combine audio chunks
            combined_audio = b''.join(self.audio_buffers[session_id])
            
            # For WebM/MP4: prepend header
            if audio_format in ["webm", "mp4"]:
                header_key = f"{session_id}_header"
                header = self.session_data.get(session_id, {}).get(header_key, b'')
                if header:
                    combined_audio = header + combined_audio
            
            # Clear buffer and reset chunk count
            self.audio_buffers[session_id] = []
            self.chunk_count[session_id] = 0
            self.last_chunk_time[session_id] = 0.0
            
            # Process audio
            await self.process_audio(session_id, combined_audio, audio_format)
            
        except Exception as e:
            logger.error(f"Error triggering audio processing for {session_id}: {e}")
    
    async def process_audio_chunk(self, session_id: str, audio_data: bytes, audio_format: str = "wav"):
        """Process audio chunk with silence-based triggering.
        
        Accumulates audio chunks and triggers STT after 2 seconds of silence,
        allowing the user to pause briefly without triggering a response.
        """
        try:
            import time
            
            # Initialize session buffers if needed
            if session_id not in self.audio_buffers:
                self.audio_buffers[session_id] = []
            
            # For WebM/MP4 from browser: cache the first chunk header
            if audio_format in ["webm", "mp4"]:
                header_key = f"{session_id}_header"
                if header_key not in self.session_data.get(session_id, {}):
                    if session_id not in self.session_data:
                        self.session_data[session_id] = {}
                    self.session_data[session_id][header_key] = audio_data
                    logger.info(f"Cached {audio_format} header ({len(audio_data)} bytes) for session {session_id}")
                    return
            
            # Accumulate audio and update timestamp
            self.audio_buffers[session_id].append(audio_data)
            self.chunk_count[session_id] = self.chunk_count.get(session_id, 0) + 1
            self.last_chunk_time[session_id] = time.time()
            buffer_size = sum(len(chunk) for chunk in self.audio_buffers[session_id])
            
            # Start silence check task if not already running
            existing_task = self.silence_check_tasks.get(session_id)
            if existing_task is None or existing_task.done():
                self.silence_check_tasks[session_id] = asyncio.create_task(
                    self._check_silence_and_process(session_id, audio_format)
                )
            
            # Safety limit: force process if buffer gets too large
            if buffer_size >= self.MAX_BUFFER_BYTES:
                logger.info(f"📦 Buffer limit reached ({buffer_size} bytes), forcing STT")
                # Cancel silence check task
                if session_id in self.silence_check_tasks:
                    task = self.silence_check_tasks[session_id]
                    if task and not task.done():
                        task.cancel()
                await self._trigger_audio_processing(session_id, audio_format)
                
        except Exception as e:
            logger.error(f"Error processing audio chunk for {session_id}: {str(e)}")
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Error processing audio: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def process_audio(self, session_id: str, audio_data: bytes, audio_format: str = "wav"):
        """Process complete audio and generate response using streaming pipeline.
        
        Enhanced with:
        - Query sequencing (latest query wins, old queries are skipped)
        - Streaming LLM->TTS (sentence-by-sentence for low latency)
        - Interrupt detection (check before each sentence)
        - Stop condition detection (farewell phrases)
        - Context & State Management (restore understanding)
        """
        # Get current query sequence and increment it
        current_query_id = self.query_sequences.get(session_id, 0) + 1
        self.query_sequences[session_id] = current_query_id
        
        try:
            # Send processing status
            await self.send_message(session_id, {
                "type": "processing",
                "message": "Processing audio...",
                "query_id": current_query_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Get session data early so we can use session-specific VoiceProcessor
            session_data = self.session_data.get(session_id, {})
            
            # Convert speech to text (use session-specific VoiceProcessor if available)
            voice_processor = session_data.get("voice_processor", self.default_voice_processor)
            stt_result = await voice_processor.process_voice_input(audio_data, audio_format)
            
            if not stt_result["success"]:
                await self.send_message(session_id, {
                    "type": "error",
                    "message": "Speech-to-text failed",
                    "error": stt_result.get("error"),
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            user_text = stt_result["text"]
            
            # Validate transcript - filter out noise phrases
            if not _is_valid_transcript(user_text):
                logger.info(f"🔇 Filtered noise transcript, skipping LLM: '{user_text}'")
                return
            
            # Check if this query is still current (might have been superseded)
            if self.query_sequences.get(session_id, 0) != current_query_id:
                logger.info(f"⏭️ Query #{current_query_id} outdated after STT, skipping")
                return
            
            # Send transcribed text
            await self.send_message(session_id, {
                "type": "transcription",
                "text": user_text,
                "query_id": current_query_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Reset inactivity timer - user spoke
            import time
            self.last_user_speech_time[session_id] = time.time()
            self.inactivity_reminder_count[session_id] = 0
            
            # Save user message to MongoDB
            try:
                chat_store = MongoDBChatStore()
                await chat_store.add_message(session_id, "user", user_text)
            except Exception as e:
                logger.warning(f"Failed to save user message to MongoDB: {e}")
            
            # Get config from session data
            config = session_data.get("config", {})
            
            # Get conversation history for context
            conversation_history = session_data.get("conversation_history", [])
            logger.info(f"📚 Query #{current_query_id}: '{user_text[:50]}...' (history: {len(conversation_history)} interactions)")
            
            # Check if this is an unclear question (what?, huh?, etc.)
            effective_user_text = user_text
            if _is_unclear_question(user_text):
                logger.info(f"❓ Detected unclear question: '{user_text}'")
                
                # Check if we have a previous unanswered question to use as context
                last_question = self.last_user_question.get(session_id, "")
                was_answered = self.last_question_answered.get(session_id, True)
                
                if last_question and not was_answered:
                    # Use previous question as context
                    logger.info(f"📝 Using previous question for context: '{last_question[:50]}...'")
                    effective_user_text = f"The user said '{user_text}' after I was explaining something. They might want me to repeat or clarify. My previous response was about: {last_question}"
                else:
                    # No context available - ask for clarification
                    logger.info("🤷 No previous context, asking for clarification")
                    effective_user_text = "The user said something unclear like 'what' or 'huh'. Politely ask them to repeat their question."
            else:
                # This is a meaningful question - track it
                self.last_user_question[session_id] = user_text
                self.last_question_answered[session_id] = False
            
            # Prepare context with persona config if available
            persona_config = config.get("persona_config")
            context = self.conversation_manager._prepare_context(session_data, persona_config)
            system_prompt = config.get("system_prompt")
            
            # Mark AI as speaking
            self.ai_speaking[session_id] = True
            
            # ===== STREAMING LLM -> TTS PIPELINE =====
            # Generate response sentence-by-sentence for low latency
            full_response = ""
            sentence_count = 0
            
            # Get model config from session
            inference_model = config.get("inference_model")
            tts_voice = config.get("tts_voice", "alloy")
            
            logger.info(f"🚀 Starting streaming pipeline for Query #{current_query_id}")
            
            # Create sentence stream from LLM
            sentence_stream = self.conversation_manager._generate_response_streaming(
                context=context,
                user_input=effective_user_text,
                conversation_history=conversation_history,
                persona_config=None,
                model=inference_model,
                temperature=None,
                max_tokens=200,
                custom_system_prompt=system_prompt
            )
            
            # Wrap with clause-based streaming for faster first-audio
            async for clause in self._generate_clauses_from_stream(sentence_stream):
                # Check if query was cancelled during streaming (interrupt detected)
                if self.query_sequences.get(session_id, 0) != current_query_id:
                    logger.info(f"⏭️ Query #{current_query_id} cancelled during streaming")
                    self.ai_speaking[session_id] = False
                    return
                
                # Skip very short fragments
                if len(clause.strip()) < 5:
                    full_response += (" " if full_response else "") + clause
                    continue
                
                sentence_count += 1
                full_response += (" " if full_response else "") + clause
                
                if sentence_count == 1:
                    logger.info(f"⚡ First clause ready for Query #{current_query_id}: '{clause[:50]}...'")
                
                # Generate TTS for this clause immediately
                tts_result = await voice_processor.generate_voice_response(clause, tts_voice)
                
                # Check again after TTS
                if self.query_sequences.get(session_id, 0) != current_query_id:
                    logger.info(f"⏭️ Query #{current_query_id} cancelled after TTS")
                    self.ai_speaking[session_id] = False
                    return
                
                if tts_result["success"]:
                    # Send audio chunk immediately (frontend queues and plays sequentially)
                    await self.send_message(session_id, {
                        "type": "audio_response",
                        "audio_base64": tts_result["audio_base64"],
                        "text": clause,
                        "format": "mp3",
                        "query_id": current_query_id,
                        "sentence_index": sentence_count,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    logger.info(f"🎤 Sent clause #{sentence_count} for Query #{current_query_id}")
            
            # Streaming complete - mark AI as not speaking
            self.ai_speaking[session_id] = False
            
            # Send full conversation response (for display)
            await self.send_message(session_id, {
                "type": "conversation_response",
                "text": full_response.strip(),
                "query_id": current_query_id,
                "sentence_count": sentence_count,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update session conversation history
            self.conversation_manager.add_to_conversation_history(
                session_data, user_text, full_response.strip()
            )
            
            # Save assistant message to MongoDB
            try:
                chat_store = MongoDBChatStore()
                await chat_store.add_message(session_id, "assistant", full_response.strip())
            except Exception as e:
                logger.warning(f"Failed to save assistant message to MongoDB: {e}")
            
            # Mark the question as answered
            self.last_question_answered[session_id] = True
            
            # Restore State Parsing & Updates (Fix for state tracking)
            # Parse the full response to update conversation state (e.g. GREETING -> TAKING_ORDER)
            parsed_response = self.conversation_manager._parse_ai_response(full_response.strip())
            
            # Manually construct response object for update (since we didn't use process_user_input)
            response_obj = {
                "text": full_response.strip(),
                "next_state": parsed_response.get("next_state"),
                "actions": parsed_response.get("actions", [])
            }
            
            # Update session state
            session_data = self.conversation_manager._update_session_from_response(
                session_data, user_text, response_obj
            )
            
            self.session_data[session_id] = session_data
            
            logger.info(f"✅ Query #{current_query_id} complete: {sentence_count} sentences. State: {session_data.get('state')}")
            
            # Check for stop condition (farewell phrases)
            if self._should_end_session(full_response):
                logger.info(f"👋 Farewell detected in Query #{current_query_id}, signaling session end")
                await self.send_message(session_id, {
                    "type": "end_session",
                    "message": "AI said goodbye, ending session",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except asyncio.CancelledError:
            logger.info(f"🛑 Query #{current_query_id} was cancelled")
            self.ai_speaking[session_id] = False
            raise
        except Exception as e:
            logger.error(f"Error processing audio for {session_id}: {str(e)}")
            self.ai_speaking[session_id] = False
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Error processing audio: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def generate_voice_response(self, session_id: str, text: str):
        """Generate voice response and send audio"""
        try:
            # Send voice generation status
            await self.send_message(session_id, {
                "type": "voice_generation",
                "message": "Generating voice response...",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Generate audio
            tts_result = await self.default_voice_processor.generate_voice_response(text, "alloy")
            
            if tts_result["success"]:
                # Send audio response
                await self.send_message(session_id, {
                    "type": "audio_response",
                    "audio_base64": tts_result["audio_base64"],
                    "text": text,
                    "format": "mp3",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                await self.send_message(session_id, {
                    "type": "error",
                    "message": "Voice generation failed",
                    "error": tts_result.get("error"),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error generating voice response for {session_id}: {str(e)}")
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Error generating voice: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def handle_text_message(self, session_id: str, message: Dict[str, Any]):
        """Handle text-based messages with streaming pipeline.
        
        Enhanced to use the same streaming LLM->TTS pattern as process_audio.
        """
        try:
            message_type = message.get("type")
            text = message.get("text", "")
            
            if message_type == "text_input":
                # Check if AI is speaking - this is an interrupt!
                if self.ai_speaking.get(session_id, False):
                    logger.info(f"🚨 Text input received while AI speaking - triggering interrupt")
                    await self.handle_interrupt(session_id)
                
                # Get current query sequence and increment it
                current_query_id = self.query_sequences.get(session_id, 0) + 1
                self.query_sequences[session_id] = current_query_id
                
                # Get session data and config
                session_data = self.session_data.get(session_id, {})
                config = session_data.get("config", {})
                conversation_history = session_data.get("conversation_history", [])
                
                logger.info(f"📝 Text Query #{current_query_id}: '{text[:50]}...' (history: {len(conversation_history)} interactions)")
                
                # Use session-specific VoiceProcessor if available (supports ElevenLabs)
                voice_processor = session_data.get("voice_processor", self.default_voice_processor)
                
                # Prepare context with persona config if available
                persona_config = config.get("persona_config")
                context = self.conversation_manager._prepare_context(session_data, persona_config)
                system_prompt = config.get("system_prompt")
                
                # Mark AI as speaking
                self.ai_speaking[session_id] = True
                
                # ===== STREAMING LLM -> TTS PIPELINE =====
                full_response = ""
                sentence_count = 0
                
                inference_model = config.get("inference_model")
                tts_voice = config.get("tts_voice", "alloy")
                
                # Create sentence stream from LLM
                sentence_stream = self.conversation_manager._generate_response_streaming(
                    context=context,
                    user_input=text,
                    conversation_history=conversation_history,
                    persona_config=None,
                    model=inference_model,
                    temperature=None,
                    max_tokens=200,
                    custom_system_prompt=system_prompt
                )
                
                # Wrap with clause-based streaming for faster first-audio
                async for clause in self._generate_clauses_from_stream(sentence_stream):
                    # Check if query was cancelled
                    if self.query_sequences.get(session_id, 0) != current_query_id:
                        logger.info(f"⏭️ Text Query #{current_query_id} cancelled during streaming")
                        self.ai_speaking[session_id] = False
                        return
                    
                    if len(clause.strip()) < 5:
                        full_response += (" " if full_response else "") + clause
                        continue
                    
                    sentence_count += 1
                    full_response += (" " if full_response else "") + clause
                    
                    # Generate and send TTS immediately
                    tts_result = await voice_processor.generate_voice_response(clause, tts_voice)
                    
                    if self.query_sequences.get(session_id, 0) != current_query_id:
                        self.ai_speaking[session_id] = False
                        return
                    
                    if tts_result["success"]:
                        await self.send_message(session_id, {
                            "type": "audio_response",
                            "audio_base64": tts_result["audio_base64"],
                            "text": clause,
                            "format": "mp3",
                            "query_id": current_query_id,
                            "sentence_index": sentence_count,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                self.ai_speaking[session_id] = False
                
                # Send full response
                await self.send_message(session_id, {
                    "type": "conversation_response",
                    "text": full_response.strip(),
                    "query_id": current_query_id,
                    "sentence_count": sentence_count,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Update history
                self.conversation_manager.add_to_conversation_history(
                    session_data, text, full_response.strip()
                )
                
                # Restore State Parsing & Updates
                parsed_response = self.conversation_manager._parse_ai_response(full_response.strip())
                
                response_obj = {
                    "text": full_response.strip(),
                    "next_state": parsed_response.get("next_state"),
                    "actions": parsed_response.get("actions", [])
                }
                
                session_data = self.conversation_manager._update_session_from_response(
                    session_data, text, response_obj
                )
                
                self.session_data[session_id] = session_data
                
                logger.info(f"✅ Text Query #{current_query_id} complete: {sentence_count} sentences. State: {session_data.get('state')}")
                
                # Check for stop condition
                if self._should_end_session(full_response):
                    await self.send_message(session_id, {
                        "type": "end_session",
                        "message": "AI said goodbye, ending session",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif message_type == "ping":
                await self.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                await self.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except asyncio.CancelledError:
            logger.info(f"🛑 Text message processing was cancelled for {session_id}")
            self.ai_speaking[session_id] = False
            raise
        except Exception as e:
            logger.error(f"Error handling text message for {session_id}: {str(e)}")
            self.ai_speaking[session_id] = False
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Error processing message: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def handle_websocket_message(self, websocket: WebSocket, session_id: str, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "audio_chunk":
                # Handle audio chunk
                audio_base64 = data.get("audio_data")
                audio_format = data.get("format", "wav")
                
                if audio_base64:
                    audio_data = base64.b64decode(audio_base64)
                    await self.process_audio_chunk(session_id, audio_data, audio_format)
            
            elif message_type == "text_input":
                # Handle text input
                await self.handle_text_message(session_id, data)
            
            elif message_type == "ping":
                # Handle ping
                await self.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif message_type == "silence_detected":
                # Frontend detected 2 seconds of silence - trigger STT
                logger.info(f"🔇 Silence detected from frontend for session {session_id}")
                # Get the audio format from session data
                audio_format = "webm"  # Default for browser
                # Trigger processing if we have buffered audio
                if session_id in self.audio_buffers and self.audio_buffers[session_id]:
                    buffer_size = sum(len(chunk) for chunk in self.audio_buffers[session_id])
                    if buffer_size > 0:
                        logger.info(f"🔇 Processing {buffer_size} bytes of buffered audio")
                        await self._trigger_audio_processing(session_id, audio_format)
            
            else:
                await self.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except json.JSONDecodeError:
            await self.send_message(session_id, {
                "type": "error",
                "message": "Invalid JSON message",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling WebSocket message for {session_id}: {str(e)}")
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Error processing message: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })

# Global instance
realtime_agent = RealTimeVoiceAgent()
