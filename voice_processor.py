import base64
import logging
from typing import Any, Dict, Optional

from tools import SpeechToTextTool, TextToSpeechTool


logger = logging.getLogger(__name__)


class VoiceProcessor:
    """Facade combining individual tools into higher level workflows."""

    def __init__(
        self,
        speech_tool: Optional[SpeechToTextTool] = None,
        tts_tool: Optional[TextToSpeechTool] = None,
    ) -> None:
        self.speech_tool = speech_tool or SpeechToTextTool()
        self.tts_tool = tts_tool or TextToSpeechTool()

    async def speech_to_text(self, audio_data: bytes, format: str = "wav") -> str:
        """Convert speech audio to text using the speech tool."""
        result = await self.speech_tool.transcribe(audio_data, format)
        if not result["success"]:
            error_message = result.get("error", "Unknown transcription error")
            logger.error("Speech-to-text failed: %s", error_message)
            raise Exception(f"Speech-to-text processing failed: {error_message}")

        return result["text"]

    async def text_to_speech(self, text: str, voice: str = "alloy") -> bytes:
        """Convert text to raw audio bytes using the TTS tool."""
        result = await self.tts_tool.synthesize(text, voice)
        if not result["success"]:
            error_message = result.get("error", "Unknown synthesis error")
            logger.error("Text-to-speech failed: %s", error_message)
            raise Exception(f"Text-to-speech processing failed: {error_message}")

        return result["audio_bytes"]

    @staticmethod
    def encode_audio_to_base64(audio_bytes: bytes) -> str:
        """Encode audio bytes to base64 string for API responses."""
        return base64.b64encode(audio_bytes).decode("utf-8")

    @staticmethod
    def decode_base64_to_audio(base64_string: str) -> bytes:
        """Decode base64 string to audio bytes."""
        return base64.b64decode(base64_string.encode("utf-8"))

    async def process_voice_input(self, audio_data: bytes, format: str = "wav") -> Dict[str, Any]:
        """Complete voice processing pipeline for speech-to-text."""
        result = await self.speech_tool.transcribe(audio_data, format)
        if result["success"]:
            result.setdefault("confidence", 1.0)
        return result

    async def generate_voice_response(self, text: str, voice: str = "alloy") -> Dict[str, Any]:
        """Generate voice response from text using text-to-speech tool."""
        result = await self.tts_tool.synthesize(text, voice)
        if result["success"]:
            # Ensure base64 is present even if synthesis implementations change.
            if not result.get("audio_base64") and result.get("audio_bytes"):
                result["audio_base64"] = self.encode_audio_to_base64(result["audio_bytes"])
        return result
