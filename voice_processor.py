import openai
import io
import base64
from typing import Optional, Dict, Any
from config import OPENAI_API_KEY, VOICE_MODEL, TTS_MODEL
import logging

logger = logging.getLogger(__name__)

class VoiceProcessor:
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    async def speech_to_text(self, audio_data: bytes, format: str = "wav") -> str:
        """
        Convert speech audio to text using OpenAI Whisper
        
        Args:
            audio_data: Raw audio bytes
            format: Audio format (wav, mp3, etc.)
            
        Returns:
            Transcribed text
        """
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{format}"
            
            # Transcribe using OpenAI Whisper
            transcript = self.client.audio.transcriptions.create(
                model=VOICE_MODEL,
                file=audio_file,
                response_format="text"
            )
            
            logger.info(f"Speech-to-text successful: {transcript[:50]}...")
            return transcript.strip()
            
        except Exception as e:
            logger.error(f"Speech-to-text failed: {str(e)}")
            raise Exception(f"Speech-to-text processing failed: {str(e)}")
    
    async def text_to_speech(self, text: str, voice: str = "alloy") -> bytes:
        """
        Convert text to speech using OpenAI TTS
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Audio bytes in MP3 format
        """
        try:
            response = self.client.audio.speech.create(
                model=TTS_MODEL,
                voice=voice,
                input=text,
                response_format="mp3"
            )
            
            audio_bytes = response.content
            logger.info(f"Text-to-speech successful for text: {text[:50]}...")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Text-to-speech failed: {str(e)}")
            raise Exception(f"Text-to-speech processing failed: {str(e)}")
    
    def encode_audio_to_base64(self, audio_bytes: bytes) -> str:
        """Encode audio bytes to base64 string for API responses"""
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def decode_base64_to_audio(self, base64_string: str) -> bytes:
        """Decode base64 string to audio bytes"""
        return base64.b64decode(base64_string.encode('utf-8'))
    
    async def process_voice_input(self, audio_data: bytes, format: str = "wav") -> Dict[str, Any]:
        """
        Complete voice processing pipeline
        
        Args:
            audio_data: Raw audio bytes
            format: Audio format
            
        Returns:
            Dictionary with transcription result
        """
        try:
            text = await self.speech_to_text(audio_data, format)
            return {
                "success": True,
                "text": text,
                "confidence": 1.0  # OpenAI doesn't provide confidence scores
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": None
            }
    
    async def generate_voice_response(self, text: str, voice: str = "alloy") -> Dict[str, Any]:
        """
        Generate voice response from text
        
        Args:
            text: Text to convert to speech
            voice: Voice to use
            
        Returns:
            Dictionary with audio response
        """
        try:
            audio_bytes = await self.text_to_speech(text, voice)
            audio_base64 = self.encode_audio_to_base64(audio_bytes)
            
            return {
                "success": True,
                "audio_base64": audio_base64,
                "text": text,
                "format": "mp3"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "audio_base64": None
            }
