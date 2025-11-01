"""
Real-time Voice Agent WebSocket Handler
This module provides real-time voice processing using WebSockets and streaming audio.
"""

import asyncio
import json
import base64
import logging
from typing import Dict, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import io

from voice_processor import VoiceProcessor
from conversation_manager import ConversationManager
from database import SessionLocal
from config import MAX_AUDIO_FILE_SIZE, ALLOWED_AUDIO_FORMATS

logger = logging.getLogger(__name__)

class RealTimeVoiceAgent:
    """Real-time voice agent for WebSocket connections"""
    
    def __init__(self):
        self.voice_processor = VoiceProcessor()
        self.conversation_manager = ConversationManager()
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.audio_buffers: Dict[str, List[bytes]] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.audio_buffers[session_id] = []
        
        # Initialize session data
        self.session_data[session_id] = self.conversation_manager.create_session()
        
        logger.info(f"WebSocket connected for session: {session_id}")
        
        # Send welcome message
        await self.send_message(session_id, {
            "type": "connection_established",
            "message": "Connected to real-time voice agent",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def disconnect(self, session_id: str):
        """Handle WebSocket disconnection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        if session_id in self.audio_buffers:
            del self.audio_buffers[session_id]
        
        logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {str(e)}")
                await self.disconnect(session_id)
    
    async def process_audio_chunk(self, session_id: str, audio_data: bytes, audio_format: str = "wav"):
        """Process audio chunk in real-time"""
        try:
            # Add audio to buffer
            if session_id not in self.audio_buffers:
                self.audio_buffers[session_id] = []
            
            self.audio_buffers[session_id].append(audio_data)
            
            # Process when buffer reaches certain size (e.g., 2 seconds of audio)
            buffer_size = sum(len(chunk) for chunk in self.audio_buffers[session_id])
            
            if buffer_size > 32000:  # ~2 seconds of 16kHz audio
                # Combine audio chunks
                combined_audio = b''.join(self.audio_buffers[session_id])
                
                # Clear buffer
                self.audio_buffers[session_id] = []
                
                # Process audio
                await self.process_audio(session_id, combined_audio, audio_format)
                
        except Exception as e:
            logger.error(f"Error processing audio chunk for {session_id}: {str(e)}")
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Error processing audio: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def process_audio(self, session_id: str, audio_data: bytes, audio_format: str = "wav"):
        """Process complete audio and generate response"""
        try:
            # Send processing status
            await self.send_message(session_id, {
                "type": "processing",
                "message": "Processing audio...",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Convert speech to text
            stt_result = await self.voice_processor.process_voice_input(audio_data, audio_format)
            
            if not stt_result["success"]:
                await self.send_message(session_id, {
                    "type": "error",
                    "message": "Speech-to-text failed",
                    "error": stt_result.get("error"),
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            user_text = stt_result["text"]
            
            # Send transcribed text
            await self.send_message(session_id, {
                "type": "transcription",
                "text": user_text,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Process conversation
            session_data = self.session_data.get(session_id, {})
            
            # Process user input
            result = await self.conversation_manager.process_user_input(
                session_data, user_text
            )
            
            # Update session data
            self.session_data[session_id] = result["session_data"]
            
            # Send conversation response
            await self.send_message(session_id, {
                "type": "conversation_response",
                "text": result["response"],
                "next_state": result.get("next_state"),
                "actions": result.get("actions", []),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Generate voice response
            await self.generate_voice_response(session_id, result["response"])
                
        except Exception as e:
            logger.error(f"Error processing audio for {session_id}: {str(e)}")
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
            tts_result = await self.voice_processor.generate_voice_response(text, "alloy")
            
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
        """Handle text-based messages"""
        try:
            message_type = message.get("type")
            text = message.get("text", "")
            
            if message_type == "text_input":
                # Process text input directly
                session_data = self.session_data.get(session_id, {})
                
                # Process user input
                result = await self.conversation_manager.process_user_input(
                    session_data, text
                )
                
                # Update session data
                self.session_data[session_id] = result["session_data"]
                
                # Send conversation response
                await self.send_message(session_id, {
                    "type": "conversation_response",
                    "text": result["response"],
                    "next_state": result.get("next_state"),
                    "actions": result.get("actions", []),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Generate voice response
                await self.generate_voice_response(session_id, result["response"])
            
            elif message_type == "ping":
                # Respond to ping
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
                
        except Exception as e:
            logger.error(f"Error handling text message for {session_id}: {str(e)}")
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
