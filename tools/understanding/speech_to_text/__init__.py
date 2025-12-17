"""Speech-to-text tool wrapping OpenAI Whisper access."""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, Optional

import openai

from config import OPENAI_API_KEY, VOICE_MODEL


logger = logging.getLogger(__name__)


class SpeechToTextTool:
    """Tool responsible for converting speech audio into text."""

    def __init__(self, client: Optional[openai.OpenAI] = None) -> None:
        self.client = client or openai.OpenAI(api_key=OPENAI_API_KEY)

    async def transcribe(
        self,
        audio_data: bytes,
        file_format: str = "wav",
        model: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe raw audio bytes into text using OpenAI Whisper.
        
        Args:
            audio_data: Raw audio bytes to transcribe
            file_format: Audio file format (default: "wav")
            model: Optional STT model override (e.g., "whisper-1")
            language: Optional language hint (ISO 639-1 code, e.g., "en", "hi")
        """
        if not audio_data:
            return {
                "success": False,
                "error": "No audio data provided.",
                "text": None,
                "detected_language": None,
            }

        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{file_format}"

            # Use provided model or fall back to config default
            stt_model = model or VOICE_MODEL

            # Build transcription kwargs
            transcribe_kwargs = {
                "model": stt_model,
                "file": audio_file,
                "response_format": "verbose_json",  # Get detected language
            }
            
            # Force default language if not specified (prevents foreign hallucination from noise)
            from tools.provider_factory import DEFAULT_LANGUAGE
            if not language:
                language = DEFAULT_LANGUAGE
            transcribe_kwargs["language"] = language
            
            # Add prompt to help Whisper handle phone audio (reduces hallucinations)
            # This guides the model to expect phone call audio with potential noise
            transcribe_kwargs["prompt"] = "Phone call audio transcription. Clear speech."

            transcript = self.client.audio.transcriptions.create(**transcribe_kwargs)

            text = transcript.text.strip()
            detected_language = getattr(transcript, 'language', language or 'en')
            
            logger.info("Speech-to-text successful (lang=%s): %s", detected_language, text[:80])
            return {
                "success": True,
                "text": text,
                "detected_language": detected_language,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Speech-to-text failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "text": None,
                "detected_language": None,
            }

