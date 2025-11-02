"""Text-to-speech tool wrapping OpenAI TTS capabilities."""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional

import openai

from config import OPENAI_API_KEY, TTS_MODEL


logger = logging.getLogger(__name__)


class TextToSpeechTool:
    """Tool responsible for converting text into playable audio."""

    def __init__(self, client: Optional[openai.OpenAI] = None) -> None:
        self.client = client or openai.OpenAI(api_key=OPENAI_API_KEY)

    async def synthesize(self, text: str, voice: str = "alloy") -> Dict[str, Any]:
        """Generate speech audio for the provided text."""
        if not text:
            return {
                "success": False,
                "error": "Text is required for synthesis.",
                "audio_base64": None,
                "audio_bytes": None,
            }

        try:
            response = self.client.audio.speech.create(
                model=TTS_MODEL,
                voice=voice,
                input=text,
                response_format="mp3",
            )

            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info("Text-to-speech generated for: %s", text[:80])
            return {
                "success": True,
                "audio_base64": audio_base64,
                "audio_bytes": audio_bytes,
                "text": text,
                "format": "mp3",
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Text-to-speech failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "audio_base64": None,
                "audio_bytes": None,
            }

