"""ElevenLabs Speech-to-Text adapter using Scribe model."""

from __future__ import annotations

import io
import logging
import httpx
from typing import Any, Dict, Optional

from config import ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)


class ElevenLabsSpeechToTextTool:
    """Tool for converting speech audio into text using ElevenLabs Scribe API."""

    ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
    
    # Available models
    MODELS = {
        "elevenlabs-scribe-v1": "scribe_v1",  # High accuracy, 99 languages
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or ELEVENLABS_API_KEY
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured. STT will fail.")

    async def transcribe(
        self,
        audio_data: bytes,
        file_format: str = "wav",
        model: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe raw audio bytes into text using ElevenLabs Scribe.
        
        Args:
            audio_data: Raw audio bytes to transcribe
            file_format: Audio file format (default: "wav")
            model: STT model to use (default: "elevenlabs-scribe-v1")
            language_code: Optional language code (e.g., "en" for English)
        
        Returns:
            Dict with success, text, and error fields
        """
        if not audio_data:
            return {
                "success": False,
                "error": "No audio data provided.",
                "text": None,
            }

        if not self.api_key:
            return {
                "success": False,
                "error": "ElevenLabs API key not configured.",
                "text": None,
            }

        try:
            # Map model name to ElevenLabs model ID
            model_id = self.MODELS.get(model, "scribe_v1")
            
            # Prepare the audio file
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{file_format}"

            # Build form data with accuracy-enhancing options
            files = {
                "file": (f"audio.{file_format}", audio_file, f"audio/{file_format}")
            }
            data = {
                "model_id": model_id,
                "tag_audio_events": "true",  # Helps with noisy phone audio
                "timestamps_granularity": "word",  # Word-level accuracy
            }
            if language_code:
                data["language_code"] = language_code

            headers = {
                "xi-api-key": self.api_key,
            }

            # Make async HTTP request to ElevenLabs STT API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.ELEVENLABS_STT_URL,
                    headers=headers,
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    error_msg = f"ElevenLabs STT API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "text": None,
                    }

                result = response.json()
                text = result.get("text", "").strip()
                
                logger.info("ElevenLabs STT successful: %s", text[:80] if text else "(empty)")
                return {
                    "success": True,
                    "text": text,
                }

        except Exception as exc:
            logger.error("ElevenLabs STT failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "text": None,
            }
