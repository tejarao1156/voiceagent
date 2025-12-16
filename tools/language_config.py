"""Language configuration for STT and TTS models.

Provides language support definitions for different speech models,
enabling the UI to show available languages based on selected models.
"""

from typing import List, Dict, Any, Set

# Supported languages per STT model
STT_LANGUAGES: Dict[str, List[Dict[str, str]]] = {
    "whisper-1": [  # OpenAI Whisper - 57+ languages
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "it", "name": "Italian"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "zh", "name": "Chinese"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "hi", "name": "Hindi"},
        {"code": "te", "name": "Telugu"},
        {"code": "ta", "name": "Tamil"},
        {"code": "ar", "name": "Arabic"},
        {"code": "ru", "name": "Russian"},
        {"code": "nl", "name": "Dutch"},
        {"code": "pl", "name": "Polish"},
        {"code": "tr", "name": "Turkish"},
        {"code": "vi", "name": "Vietnamese"},
        {"code": "th", "name": "Thai"},
        {"code": "id", "name": "Indonesian"},
        {"code": "ms", "name": "Malay"},
        {"code": "fil", "name": "Filipino"},
        {"code": "bn", "name": "Bengali"},
        {"code": "gu", "name": "Gujarati"},
        {"code": "kn", "name": "Kannada"},
        {"code": "ml", "name": "Malayalam"},
        {"code": "mr", "name": "Marathi"},
        {"code": "pa", "name": "Punjabi"},
        {"code": "ur", "name": "Urdu"},
    ],
    "elevenlabs-scribe-v1": [  # ElevenLabs Scribe - 99 languages
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "it", "name": "Italian"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "zh", "name": "Chinese"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "hi", "name": "Hindi"},
        {"code": "te", "name": "Telugu"},
        {"code": "ta", "name": "Tamil"},
        {"code": "ar", "name": "Arabic"},
        {"code": "ru", "name": "Russian"},
        {"code": "nl", "name": "Dutch"},
        {"code": "pl", "name": "Polish"},
        {"code": "tr", "name": "Turkish"},
        {"code": "vi", "name": "Vietnamese"},
        {"code": "th", "name": "Thai"},
        {"code": "id", "name": "Indonesian"},
        {"code": "ms", "name": "Malay"},
        {"code": "fil", "name": "Filipino"},
        {"code": "bn", "name": "Bengali"},
        {"code": "gu", "name": "Gujarati"},
        {"code": "kn", "name": "Kannada"},
        {"code": "ml", "name": "Malayalam"},
        {"code": "mr", "name": "Marathi"},
        {"code": "pa", "name": "Punjabi"},
        {"code": "ur", "name": "Urdu"},
    ],
}

# TTS languages (for voice output)
TTS_LANGUAGES: Dict[str, List[Dict[str, str]]] = {
    "tts-1": [{"code": "en", "name": "English"}],  # OpenAI TTS - English primarily
    "tts-1-hd": [{"code": "en", "name": "English"}],  # OpenAI TTS HD - English primarily
    "eleven_turbo_v2_5": [{"code": "en", "name": "English"}],  # ElevenLabs - English optimized
    "eleven_flash_v2_5": [{"code": "en", "name": "English"}],  # ElevenLabs Flash - English
    "eleven_multilingual_v2": [  # ElevenLabs Multilingual - 29 languages
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "it", "name": "Italian"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "zh", "name": "Chinese"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "hi", "name": "Hindi"},
        {"code": "ar", "name": "Arabic"},
        {"code": "ru", "name": "Russian"},
        {"code": "nl", "name": "Dutch"},
        {"code": "pl", "name": "Polish"},
        {"code": "tr", "name": "Turkish"},
        {"code": "vi", "name": "Vietnamese"},
        {"code": "id", "name": "Indonesian"},
        {"code": "fil", "name": "Filipino"},
    ],
}

# Language code to name mapping for quick lookup
LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "es": "Spanish", 
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "ar": "Arabic",
    "ru": "Russian",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "fil": "Filipino",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "pa": "Punjabi",
    "ur": "Urdu",
}


def get_stt_languages(model: str) -> List[Dict[str, str]]:
    """Get supported languages for an STT model."""
    return STT_LANGUAGES.get(model, [{"code": "en", "name": "English"}])


def get_tts_languages(model: str) -> List[Dict[str, str]]:
    """Get supported languages for a TTS model."""
    return TTS_LANGUAGES.get(model, [{"code": "en", "name": "English"}])


def get_supported_languages(stt_model: str, tts_model: str) -> List[Dict[str, str]]:
    """Get languages supported by BOTH STT and TTS models (intersection).
    
    This ensures the user can speak AND hear responses in the same language.
    
    Args:
        stt_model: The STT model name (e.g., "whisper-1", "elevenlabs-scribe-v1")
        tts_model: The TTS model name (e.g., "tts-1", "eleven_multilingual_v2")
    
    Returns:
        List of language dicts with "code" and "name" keys
    """
    stt_langs = STT_LANGUAGES.get(stt_model, [{"code": "en", "name": "English"}])
    tts_langs = TTS_LANGUAGES.get(tts_model, [{"code": "en", "name": "English"}])
    
    # Get intersection of language codes
    stt_codes: Set[str] = {lang["code"] for lang in stt_langs}
    tts_codes: Set[str] = {lang["code"] for lang in tts_langs}
    common_codes = stt_codes & tts_codes
    
    # Return languages that are in both, maintaining order from STT list
    result = [lang for lang in stt_langs if lang["code"] in common_codes]
    
    # Always ensure English is available as fallback
    if not result:
        result = [{"code": "en", "name": "English"}]
    
    return result


def is_language_supported(language_code: str, allowed_languages: List[str]) -> bool:
    """Check if a language code is in the allowed list.
    
    Args:
        language_code: ISO 639-1 language code (e.g., "en", "hi")
        allowed_languages: List of allowed language codes
    
    Returns:
        True if language is supported
    """
    return language_code in allowed_languages


def get_language_names(language_codes: List[str]) -> List[str]:
    """Convert language codes to human-readable names.
    
    Args:
        language_codes: List of ISO 639-1 codes (e.g., ["en", "hi", "te"])
    
    Returns:
        List of language names (e.g., ["English", "Hindi", "Telugu"])
    """
    return [LANGUAGE_NAMES.get(code, code) for code in language_codes]
