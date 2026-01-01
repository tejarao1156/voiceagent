"""Deepgram Text-to-Speech adapter using Aura voices."""

from __future__ import annotations

import logging
import asyncio
import io
from typing import Any, Dict, Optional, List

try:
    # Only import Client, use dicts for options to avoid version issues
    from deepgram import DeepgramClient
    HAS_DEEPGRAM = True
except ImportError:
    HAS_DEEPGRAM = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

from config import DEEPGRAM_API_KEY

logger = logging.getLogger(__name__)


class DeepgramTextToSpeechTool:
    """Tool for converting text to speech using Deepgram Aura API.
    
    Deepgram Aura is optimized for low-latency, conversational AI applications.
    Returns audio in various formats including PCM for direct Twilio streaming.
    """

    # Available Aura voices (format: aura-{voice}-en)
    AURA_VOICES = {
        "asteria": "Female, warm and professional",
        "luna": "Female, friendly and conversational",
        "stella": "Female, clear and articulate",
        "athena": "Female, confident and authoritative",
        "hera": "Female, calm and soothing",
        "orion": "Male, warm and professional",
        "arcas": "Male, friendly and conversational",
        "perseus": "Male, clear and articulate",
        "angus": "Male, confident and authoritative",
        "orpheus": "Male, calm and soothing",
        "helios": "Male, energetic and enthusiastic",
        "zeus": "Male, deep and commanding"
    }

    # Default model
    DEFAULT_MODEL = "aura-asteria-en"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Deepgram TTS client."""
        self.api_key = api_key or DEEPGRAM_API_KEY
        self.client = None
        
        if not HAS_DEEPGRAM:
            logger.warning("⚠️ deepgram-sdk not installed. Run: pip install deepgram-sdk")
            return
            
        if not self.api_key:
            logger.warning("⚠️ DEEPGRAM_API_KEY not set. Deepgram TTS will not work.")
            return
            
        try:
            self.client = DeepgramClient(api_key=self.api_key)
            logger.info("✅ Deepgram TTS client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Deepgram TTS client: {e}")

    def _get_model_name(self, voice: str) -> str:
        """Convert voice name to full model name.
        
        Args:
            voice: Voice name (e.g., "asteria") or full model (e.g., "aura-asteria-en")
            
        Returns:
            Full model name like "aura-asteria-en"
        """
        if voice.startswith("aura-"):
            return voice
        # Assume English if no language specified
        return f"aura-{voice.lower()}-en"

    async def synthesize(
        self,
        text: str,
        voice: str = "asteria",
        encoding: str = "mp3",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate speech audio from text.
        
        Args:
            text: Text to convert to speech
            voice: Voice name (e.g., "asteria", "orion") or full model
            encoding: Output format ("mp3", "linear16", "mulaw", "alaw")
            **kwargs: Additional options
            
        Returns:
            Dict with 'audio' (bytes), 'format', and 'duration_ms'
        """
        if not self.client:
            logger.error("Deepgram TTS client not initialized")
            return {"audio": b"", "error": "Client not initialized"}

        # Edge case: Empty text
        if not text or len(text.strip()) == 0:
            logger.warning("⚠️ Empty text provided to Deepgram TTS")
            return {"audio": b"", "error": "Empty text"}
        
        # Edge case: Text too long (Deepgram has limits)
        if len(text) > 5000:
            logger.warning(f"⚠️ Text very long ({len(text)} chars), may need chunking")
        
        # Voice validation - fallback to default if invalid
        voice_lower = voice.lower().replace("aura-", "").replace("-en", "")
        if voice_lower not in self.AURA_VOICES:
            logger.warning(f"⚠️ Unknown voice '{voice}', falling back to asteria")
            voice = "asteria"

        try:
            model = self._get_model_name(voice)
            
            options = {
                "model": model,
                "encoding": encoding,
                **kwargs
            }

            # Generate speech
            # SDK v3+ structure: client.speak.v1.audio.generate(text=..., **kwargs) -> Iterator[bytes]
            response_iterator = await asyncio.to_thread(
                self.client.speak.v1.audio.generate,
                text=text,
                **options
            )

            # Consuming the iterator to get bytes
            if response_iterator:
                # Iterate and collect bytes (it's a sync iterator)
                audio_data = b"".join(response_iterator)
                logger.info(f"✅ Deepgram TTS generated {len(audio_data)} bytes for '{text[:30]}...'")
                return {
                    "audio": audio_data,
                    "format": encoding,
                    "model": model
                }

            logger.warning("⚠️ Deepgram TTS returned empty response")
            return {"audio": b"", "format": encoding}

        except Exception as e:
            logger.error(f"❌ Deepgram TTS error: {e}")
            return {"audio": b"", "error": str(e)}

    async def synthesize_stream(
        self,
        text: str,
        voice: str = "asteria",
        encoding: str = "mulaw",
        **kwargs
    ) -> Iterator[bytes]:
        """Generate TTS and return an iterator of audio chunks."""
        if not self.client:
            logger.error("Deepgram TTS client not initialized")
            return iter([])

        # Voice validation
        voice_lower = voice.lower().replace("aura-", "").replace("-en", "")
        if voice_lower not in self.AURA_VOICES:
            voice_lower = "asteria"

        try:
            model = self._get_model_name(voice_lower)
            
            options = {
                "model": model,
                "encoding": encoding,
                **kwargs
            }

            # SDK v3+ structure: client.speak.v1.audio.generate(text=..., **kwargs) -> Iterator[bytes]
            response_iterator = await asyncio.to_thread(
                self.client.speak.v1.audio.generate,
                text=text,
                **options
            )
            
            return response_iterator

        except Exception as e:
            logger.error(f"❌ Deepgram TTS stream error: {e}")
            return iter([])

        self,
        text: str,
        voice: str = "asteria",
        encoding: str = "mp3",
        **kwargs
    ) -> Dict[str, Any]:
        """Synchronous version of synthesize."""
        if not self.client:
            logger.error("Deepgram TTS client not initialized")
            return {"audio": b"", "error": "Client not initialized"}

        try:
            model = self._get_model_name(voice)
            
            options = {
                "model": model,
                "encoding": encoding,
                **kwargs
            }

            # SDK v3+ structure: client.speak.v1.audio.generate(text=..., **kwargs)
            response_iterator = self.client.speak.v1.audio.generate(
                text=text,
                **options
            )

            if response_iterator:
                audio_data = b"".join(response_iterator)
                logger.info(f"✅ Deepgram TTS generated {len(audio_data)} bytes")
                return {
                    "audio": audio_data,
                    "format": encoding,
                    "model": model
                }

            return {"audio": b"", "format": encoding}

        except Exception as e:
            logger.error(f"❌ Deepgram TTS error: {e}")
            return {"audio": b"", "error": str(e)}

    def synthesize_pcm(
        self,
        text: str,
        voice: str = "asteria",
        sample_rate: int = 8000,
        **kwargs
    ) -> bytes:
        """Generate PCM audio for Twilio streaming (mulaw 8kHz).
        
        Twilio Media Streams expect mulaw audio at 8kHz.
        
        Args:
            text: Text to convert
            voice: Aura voice name
            sample_rate: Sample rate (8000 for Twilio)
            
        Returns:
            Raw mulaw audio bytes suitable for Twilio
        """
        if not self.client:
            logger.error("Deepgram TTS client not initialized")
            return b""

        try:
            model = self._get_model_name(voice)
            
            # Request mulaw encoding for Twilio compatibility
            options = {
                "model": model,
                "encoding": "mulaw",
                "sample_rate": sample_rate,
                **kwargs
            }

            # SDK v3+ structure: client.speak.v1.audio.generate(text=..., **kwargs)
            response_iterator = self.client.speak.v1.audio.generate(
                text=text,
                **options
            )

            if response_iterator:
                audio_data = b"".join(response_iterator)
                logger.info(f"✅ Deepgram TTS (PCM) generated {len(audio_data)} bytes")
                return audio_data

            return b""

        except Exception as e:
            logger.error(f"❌ Deepgram TTS PCM error: {e}")
            return b""

    @staticmethod
    def get_available_voices() -> Dict[str, str]:
        """Return available Aura voices with descriptions."""
        return DeepgramTextToSpeechTool.AURA_VOICES

    @staticmethod
    def list_voices() -> List[Dict[str, str]]:
        """Return voices in a format compatible with UI dropdowns."""
        return [
            {"id": f"aura-{name}-en", "name": name.capitalize(), "description": desc}
            for name, desc in DeepgramTextToSpeechTool.AURA_VOICES.items()
        ]
