"""Deepgram Speech-to-Text adapter with streaming support."""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, Optional, List

try:
    # Only import Client, use dicts for options to avoid version issues
    from deepgram import DeepgramClient
    HAS_DEEPGRAM = True
except ImportError:
    HAS_DEEPGRAM = False

from config import DEEPGRAM_API_KEY

logger = logging.getLogger(__name__)


class DeepgramSpeechToTextTool:
    """Tool for converting speech to text using Deepgram API.
    
    Supports both file-based transcription and real-time streaming.
    Deepgram models: nova-2, nova-3 (latest), base, enhanced
    """

    # Default models - nova-3 is the latest and most accurate
    DEFAULT_MODEL = "nova-2"
    
    # Supported models
    SUPPORTED_MODELS = {
        "nova-3": "Latest, most accurate model",
        "nova-2": "Previous generation, very accurate",
        "enhanced": "Enhanced accuracy model",
        "base": "Base model, fastest"
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Deepgram STT client."""
        self.api_key = api_key or DEEPGRAM_API_KEY
        self.client = None
        
        if not HAS_DEEPGRAM:
            logger.warning("⚠️ deepgram-sdk not installed. Run: pip install deepgram-sdk")
            return
            
        if not self.api_key:
            logger.warning("⚠️ DEEPGRAM_API_KEY not set. Deepgram STT will not work.")
            return
            
        try:
            self.client = DeepgramClient(api_key=self.api_key)
            logger.info("✅ Deepgram STT client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Deepgram client: {e}")

    async def transcribe(
        self,
        audio_data: bytes,
        model: str = "nova-2",
        language: str = "en",
        punctuate: bool = True,
        smart_format: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes (WAV, MP3, etc.)
            model: Deepgram model (nova-2, nova-3, enhanced, base)
            language: Language code (e.g., "en", "es", "fr")
            punctuate: Add punctuation to transcript
            smart_format: Apply smart formatting (dates, numbers, currency)
            **kwargs: Additional Deepgram options
            
        Returns:
            Dict with 'text' (transcript) and 'confidence' score
        """
        if not self.client:
            logger.error("Deepgram client not initialized")
            return {"text": "", "confidence": 0.0, "error": "Client not initialized"}

        # Edge case: Empty audio
        if not audio_data or len(audio_data) == 0:
            logger.warning("⚠️ Empty audio data provided to Deepgram STT")
            return {"text": "", "confidence": 0.0, "error": "Empty audio data"}
        
        # Edge case: Audio too small (likely noise/silence)
        if len(audio_data) < 1000:  # Less than ~1KB is likely too short
            logger.warning(f"⚠️ Audio data very small ({len(audio_data)} bytes), may be silence")
        
        # Model validation - fallback to default if invalid
        if model not in self.SUPPORTED_MODELS:
            logger.warning(f"⚠️ Unknown model '{model}', falling back to {self.DEFAULT_MODEL}")
            model = self.DEFAULT_MODEL

        try:
            # Build options
            options = {
                "model": model,
                "language": language,
                "punctuate": punctuate,
                "smart_format": smart_format,
                **kwargs
            }

            # Transcribe the audio
            # SDK v3+ signature: transcribe_file(*, request, **kwargs) - all kwargs
            response = await asyncio.to_thread(
                self.client.listen.v1.media.transcribe_file,
                request=audio_data,
                **options
            )

            # Extract transcript from response
            if response and response.results:
                channels = response.results.channels
                if channels and len(channels) > 0:
                    alternatives = channels[0].alternatives
                    if alternatives and len(alternatives) > 0:
                        transcript = alternatives[0].transcript
                        confidence = alternatives[0].confidence
                        
                        logger.info(f"✅ Deepgram transcribed: '{transcript[:50]}...' (confidence: {confidence:.2f})")
                        return {
                            "text": transcript,
                            "confidence": confidence,
                            "words": alternatives[0].words if hasattr(alternatives[0], 'words') else []
                        }

            logger.warning("⚠️ Deepgram returned empty transcript")
            return {"text": "", "confidence": 0.0}

        except Exception as e:
            logger.error(f"❌ Deepgram transcription error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}

    def transcribe_sync(
        self,
        audio_data: bytes,
        model: str = "nova-2",
        language: str = "en",
        punctuate: bool = True,
        smart_format: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Synchronous version of transcribe for non-async contexts."""
        if not self.client:
            logger.error("Deepgram client not initialized")
            return {"text": "", "confidence": 0.0, "error": "Client not initialized"}

        try:
            options = PrerecordedOptions(
                model=model,
                language=language,
                punctuate=punctuate,
                smart_format=smart_format,
                **kwargs
            )

            response = self.client.listen.prerecorded.v("1").transcribe_file(
                {"buffer": audio_data},
                options
            )

            if response and response.results:
                channels = response.results.channels
                if channels and len(channels) > 0:
                    alternatives = channels[0].alternatives
                    if alternatives and len(alternatives) > 0:
                        transcript = alternatives[0].transcript
                        confidence = alternatives[0].confidence
                        
                        logger.info(f"✅ Deepgram transcribed: '{transcript[:50]}...'")
                        return {
                            "text": transcript,
                            "confidence": confidence
                        }

            return {"text": "", "confidence": 0.0}

        except Exception as e:
            logger.error(f"❌ Deepgram transcription error: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}

    @staticmethod
    def get_supported_models() -> Dict[str, str]:
        """Return supported Deepgram STT models."""
        return DeepgramSpeechToTextTool.SUPPORTED_MODELS

    @staticmethod
    def get_supported_languages() -> List[str]:
        """Return commonly supported languages."""
        return [
            "en", "en-US", "en-GB", "en-AU",
            "es", "es-ES", "es-419",
            "fr", "fr-FR", "fr-CA",
            "de", "de-DE",
            "it", "it-IT",
            "pt", "pt-BR", "pt-PT",
            "nl", "nl-NL",
            "ja", "ko", "zh", "zh-CN", "zh-TW",
            "hi", "ru", "ar", "pl", "uk", "tr"
        ]
