"""Provider factory for STT and TTS tool selection.

This factory routes to the correct provider (OpenAI or ElevenLabs) based on the model name.
It maintains backward compatibility - if no provider is specified, OpenAI is used.
"""

from __future__ import annotations

import logging
from typing import Union, Optional

# Import OpenAI tools (existing)
from tools.understanding.speech_to_text import SpeechToTextTool
from tools.response.text_to_speech import TextToSpeechTool

# Import ElevenLabs tools (new)
from tools.understanding.speech_to_text.elevenlabs_stt import ElevenLabsSpeechToTextTool
from tools.response.text_to_speech.elevenlabs_tts import ElevenLabsTextToSpeechTool

logger = logging.getLogger(__name__)


# Provider prefixes for model detection
ELEVENLABS_STT_PREFIXES = ("elevenlabs",)
ELEVENLABS_TTS_PREFIXES = ("eleven",)


def get_stt_tool(model: Optional[str] = None) -> Union[SpeechToTextTool, ElevenLabsSpeechToTextTool]:
    """Get the appropriate STT tool based on model name.
    
    Args:
        model: STT model name (e.g., "whisper-1", "elevenlabs-scribe-v1")
    
    Returns:
        SpeechToTextTool (OpenAI) or ElevenLabsSpeechToTextTool
    """
    if model and any(model.lower().startswith(prefix) for prefix in ELEVENLABS_STT_PREFIXES):
        logger.info(f"Using ElevenLabs STT for model: {model}")
        return ElevenLabsSpeechToTextTool()
    
    # Default to OpenAI
    logger.debug(f"Using OpenAI STT for model: {model}")
    return SpeechToTextTool()


def get_tts_tool(model: Optional[str] = None) -> Union[TextToSpeechTool, ElevenLabsTextToSpeechTool]:
    """Get the appropriate TTS tool based on model name.
    
    Args:
        model: TTS model name (e.g., "tts-1", "eleven_turbo_v2_5")
    
    Returns:
        TextToSpeechTool (OpenAI) or ElevenLabsTextToSpeechTool
    """
    if model and any(model.lower().startswith(prefix) for prefix in ELEVENLABS_TTS_PREFIXES):
        logger.info(f"Using ElevenLabs TTS for model: {model}")
        return ElevenLabsTextToSpeechTool()
    
    # Default to OpenAI
    logger.debug(f"Using OpenAI TTS for model: {model}")
    return TextToSpeechTool()


def is_elevenlabs_stt(model: Optional[str]) -> bool:
    """Check if the model is an ElevenLabs STT model."""
    if not model:
        return False
    return any(model.lower().startswith(prefix) for prefix in ELEVENLABS_STT_PREFIXES)


def is_elevenlabs_tts(model: Optional[str]) -> bool:
    """Check if the model is an ElevenLabs TTS model."""
    if not model:
        return False
    return any(model.lower().startswith(prefix) for prefix in ELEVENLABS_TTS_PREFIXES)
