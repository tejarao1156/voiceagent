"""Speech-to-text tool using Google Gemini API."""

from __future__ import annotations

import base64
import logging
import io
from typing import Any, Dict, Optional

try:
    import google.genai as genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


class GeminiSTTTool:
    """Tool responsible for converting speech audio into text using Google Gemini."""

    def __init__(self) -> None:
        if not HAS_GEMINI:
            logger.warning("google-genai not installed. Install with: pip install google-genai")
            self.client = None
        elif not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set in environment variables")
            self.client = None
        else:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Gemini STT client initialized successfully")

    async def transcribe(
        self, 
        audio_data: bytes, 
        file_format: str = "wav", 
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe audio using Google Gemini.
        
        Args:
            audio_data: Raw audio bytes to transcribe
            file_format: Audio file format (default: "wav")
            model: Optional model override (default: gemini-2.0-flash)
        
        Returns:
            Dict with success, text, and optional error
        """
        if not self.client:
            return {
                "success": False,
                "error": "Gemini client not initialized. Check GEMINI_API_KEY.",
                "text": None,
            }

        if not audio_data:
            return {
                "success": False,
                "error": "No audio data provided.",
                "text": None,
            }

        try:
            # Determine MIME type
            mime_types = {
                "wav": "audio/wav",
                "mp3": "audio/mp3",
                "flac": "audio/flac",
                "m4a": "audio/mp4",
                "webm": "audio/webm",
            }
            mime_type = mime_types.get(file_format.lower(), "audio/wav")
            
            # Use specified model or default
            stt_model = model or "gemini-2.0-flash"
            
            # Create inline audio data
            audio_part = types.Part.from_bytes(
                data=audio_data,
                mime_type=mime_type
            )
            
            # Send to Gemini with transcription prompt
            response = self.client.models.generate_content(
                model=stt_model,
                contents=[
                    audio_part,
                    "Transcribe this audio accurately. Return ONLY the transcribed text, nothing else."
                ]
            )
            
            # Extract text from response
            text = response.text.strip() if response.text else ""
            
            logger.info(f"Gemini STT successful: {text[:80]}")
            return {
                "success": True,
                "text": text,
            }
            
        except Exception as exc:
            logger.error(f"Gemini STT failed: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "text": None,
            }
