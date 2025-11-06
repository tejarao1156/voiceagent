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

    async def transcribe(self, audio_data: bytes, file_format: str = "wav") -> Dict[str, Any]:
        """Transcribe raw audio bytes into text using OpenAI Whisper."""
        if not audio_data:
            return {
                "success": False,
                "error": "No audio data provided.",
                "text": None,
            }

        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{file_format}"

            transcript = self.client.audio.transcriptions.create(
                model=VOICE_MODEL,
                file=audio_file,
                response_format="text",
            )

            text = transcript.strip()
            logger.info("Speech-to-text successful: %s", text[:80])
            return {
                "success": True,
                "text": text,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Speech-to-text failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "text": None,
            }

