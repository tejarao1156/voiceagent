"""Provider factory for STT and TTS tool selection.

This factory routes to the correct provider (OpenAI, ElevenLabs, or Deepgram) based on the model name.
It maintains backward compatibility - if no provider is specified, OpenAI is used.
"""

from __future__ import annotations

import logging
from typing import Union, Optional, Dict, Any

# Import OpenAI tools (existing)
from tools.understanding.speech_to_text import SpeechToTextTool
from tools.response.text_to_speech import TextToSpeechTool

# Import ElevenLabs tools
from tools.understanding.speech_to_text.elevenlabs_stt import ElevenLabsSpeechToTextTool
from tools.response.text_to_speech.elevenlabs_tts import ElevenLabsTextToSpeechTool

# Import Deepgram tools
from tools.understanding.speech_to_text.deepgram_stt import DeepgramSpeechToTextTool
from tools.response.text_to_speech.deepgram_tts import DeepgramTextToSpeechTool

logger = logging.getLogger(__name__)


# Provider prefixes for model detection
ELEVENLABS_STT_PREFIXES = ("elevenlabs",)
ELEVENLABS_TTS_PREFIXES = ("eleven",)
DEEPGRAM_STT_PREFIXES = ("deepgram", "nova", "enhanced", "base")
DEEPGRAM_TTS_PREFIXES = ("deepgram", "aura",)

# Default language for all STT models (prevents hallucination from noise)
# All STT implementations should import and use this
DEFAULT_LANGUAGE = "en"

# Default parameter mappings for each provider
# These are "production-ready" defaults that work well out of the box
DEFAULT_STT_PARAMS = {
    "openai": {
        "model": "whisper-1",
        "language": "en"
    },
    "elevenlabs": {
        "model": "scribe-v1",
        "language": "en"
    },
    "deepgram": {
        "model": "nova-2",
        "language": "en",
        "punctuate": True,
        "smart_format": True,
        "endpointing": 300  # ms of silence before ending utterance
    }
}

DEFAULT_TTS_PARAMS = {
    "openai": {
        "model": "tts-1",
        "voice": "nova"
    },
    "elevenlabs": {
        "model": "eleven_turbo_v2_5",
        "voice": "rachel",
        "stability": 0.5,
        "similarity_boost": 0.8
    },
    "deepgram": {
        "model": "aura-asteria-en",
        "voice": "asteria"
    }
}


def get_stt_tool(model: Optional[str] = None) -> Union[SpeechToTextTool, ElevenLabsSpeechToTextTool, DeepgramSpeechToTextTool]:
    """Get the appropriate STT tool based on model name.
    
    Args:
        model: STT model name (e.g., "whisper-1", "elevenlabs-scribe-v1", "nova-2", "deepgram-nova-2")
    
    Returns:
        SpeechToTextTool (OpenAI), ElevenLabsSpeechToTextTool, or DeepgramSpeechToTextTool
    """
    if model:
        model_lower = model.lower()
        
        # Check for Deepgram
        if any(model_lower.startswith(prefix) for prefix in DEEPGRAM_STT_PREFIXES):
            logger.info(f"🎤 Using Deepgram STT for model: {model}")
            return DeepgramSpeechToTextTool()
        
        # Check for ElevenLabs
        if any(model_lower.startswith(prefix) for prefix in ELEVENLABS_STT_PREFIXES):
            logger.info(f"🎤 Using ElevenLabs STT for model: {model}")
            return ElevenLabsSpeechToTextTool()
    
    # Default to OpenAI
    logger.debug(f"🎤 Using OpenAI STT for model: {model}")
    return SpeechToTextTool()


def get_tts_tool(model: Optional[str] = None) -> Union[TextToSpeechTool, ElevenLabsTextToSpeechTool, DeepgramTextToSpeechTool]:
    """Get the appropriate TTS tool based on model name.
    
    Args:
        model: TTS model name (e.g., "tts-1", "eleven_turbo_v2_5", "aura-asteria-en")
    
    Returns:
        TextToSpeechTool (OpenAI), ElevenLabsTextToSpeechTool, or DeepgramTextToSpeechTool
    """
    if model:
        model_lower = model.lower()
        
        # Check for Deepgram
        if any(model_lower.startswith(prefix) for prefix in DEEPGRAM_TTS_PREFIXES):
            logger.info(f"🔊 Using Deepgram TTS for model: {model}")
            return DeepgramTextToSpeechTool()
        
        # Check for ElevenLabs
        if any(model_lower.startswith(prefix) for prefix in ELEVENLABS_TTS_PREFIXES):
            logger.info(f"🔊 Using ElevenLabs TTS for model: {model}")
            return ElevenLabsTextToSpeechTool()
    
    # Default to OpenAI
    logger.debug(f"🔊 Using OpenAI TTS for model: {model}")
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


def is_deepgram_stt(model: Optional[str]) -> bool:
    """Check if the model is a Deepgram STT model."""
    if not model:
        return False
    return any(model.lower().startswith(prefix) for prefix in DEEPGRAM_STT_PREFIXES)


def is_deepgram_tts(model: Optional[str]) -> bool:
    """Check if the model is a Deepgram TTS model."""
    if not model:
        return False
    return any(model.lower().startswith(prefix) for prefix in DEEPGRAM_TTS_PREFIXES)


def get_stt_provider(model: Optional[str]) -> str:
    """Determine STT provider from model name."""
    if is_deepgram_stt(model):
        return "deepgram"
    if is_elevenlabs_stt(model):
        return "elevenlabs"
    return "openai"


def get_tts_provider(model: Optional[str]) -> str:
    """Determine TTS provider from model name."""
    if is_deepgram_tts(model):
        return "deepgram"
    if is_elevenlabs_tts(model):
        return "elevenlabs"
    return "openai"


def get_default_stt_params(provider: str) -> Dict[str, Any]:
    """Get default STT parameters for a provider."""
    return DEFAULT_STT_PARAMS.get(provider.lower(), DEFAULT_STT_PARAMS["openai"]).copy()


def get_default_tts_params(provider: str) -> Dict[str, Any]:
    """Get default TTS parameters for a provider."""
    return DEFAULT_TTS_PARAMS.get(provider.lower(), DEFAULT_TTS_PARAMS["openai"]).copy()

