"""ElevenLabs Text-to-Speech adapter with human-like voice synthesis."""

from __future__ import annotations

import base64
import logging
import httpx
import io
from typing import Any, Dict, Optional, List

from config import ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)


class ElevenLabsTextToSpeechTool:
    """Tool for converting text into natural, human-like speech using ElevenLabs API."""

    ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
    VOICES_URL = "https://api.elevenlabs.io/v1/voices"
    
    # Available models (ordered by quality/speed tradeoff)
    MODELS = {
        "eleven_multilingual_v2": "eleven_multilingual_v2",     # Best quality, 29 languages
        "eleven_turbo_v2_5": "eleven_turbo_v2_5",               # Low latency, good quality
        "eleven_flash_v2_5": "eleven_flash_v2_5",               # Fastest, slightly lower quality
    }
    
    # Default voice IDs (these are popular ElevenLabs voices)
    VOICE_IDS = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",      # Young American female
        "drew": "29vD33N1CtxCmqQRPOHJ",        # Middle-aged American male
        "clyde": "2EiwWnXFnvU5JabPnv8n",       # War veteran, deep voice
        "paul": "5Q0t7uMcjZakVgZMEVK4",        # Authoritative male
        "domi": "AZnzlk1XvdvUeBnXmlld",        # Young American female
        "bella": "EXAVITQu4vr4xnSDxMaL",       # Soft young female
        "antoni": "ErXwobaYiN019PkySvjV",      # Young American male
        "thomas": "GBv7mTt0atIp3Br8iCZE",      # Calm American male
        "charlie": "IKne3meq5aSn9XLyUdCD",     # Australian male
        "emily": "LcfcDJNUP1GQjkzn1xUU",       # British female
        "elli": "MF3mGyEYCl7XYWbV9V6O",        # Young American female
        "callum": "N2lVS1w4EtoT3dr4eOWO",      # Transatlantic male
        "patrick": "ODq5zmih8GrVes37Dizd",      # American male
        "harry": "SOYHLrjzK2X1ezoPC6cr",       # British male
        "liam": "TX3LPaxmHKxFdv7VOQHJ",        # American male
        "dorothy": "ThT5KcBeYPX3keUQqHPh",      # Elderly British female
        "josh": "TxGEqnHWrfWFTfGW9XjX",        # Deep American male
        "arnold": "VR6AewLTigWG4xSOukaG",      # American male
        "charlotte": "XB0fDUnXU5powFXDhCwa",   # Young Swedish female
        "matilda": "XrExE9yKIg1WjnnlVkGX",      # Young American female
        "james": "ZQe5CZNOzWyzPSCn5a3c",       # Older Australian male
        "joseph": "Zlb1dXrM653N07WRdFW3",       # British male
        "adam": "pNInz6obpgDQGcFmaJgB",        # Middle-aged American male
        "sam": "yoZ06aMxZJJ28mfd3KP",          # Young American male
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.model = "eleven_turbo_v2_5"  # Default to low-latency model
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured. TTS will fail.")

    def _get_voice_id(self, voice: str) -> str:
        """Get voice ID from voice name or return as-is if it's already an ID."""
        voice_lower = voice.lower() if voice else "rachel"
        return self.VOICE_IDS.get(voice_lower, voice)  # Return as-is if not in mapping

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        *,
        model: Optional[str] = None,
        stability: float = 0.5,           # 0.0=expressive, 1.0=stable
        similarity_boost: float = 0.8,    # How closely to match voice
        style: float = 0.0,               # Speaking style exaggeration
        use_speaker_boost: bool = True,
    ) -> Dict[str, Any]:
        """Generate speech audio from text using ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            voice: Voice name (e.g., "rachel", "drew") or voice ID
            model: TTS model to use (e.g., "eleven_turbo_v2_5")
            stability: Voice stability (0-1). Lower = more expressive/emotional
            similarity_boost: Voice clarity (0-1). Higher = clearer voice
            style: Speaking style exaggeration (0-1). Higher = more stylized
            use_speaker_boost: Boost voice similarity
        
        Returns:
            Dict with success, audio_base64, audio_bytes, and error fields
        """
        if not text:
            return {
                "success": False,
                "error": "Text is required for synthesis.",
                "audio_base64": None,
                "audio_bytes": None,
            }

        if not self.api_key:
            return {
                "success": False,
                "error": "ElevenLabs API key not configured.",
                "audio_base64": None,
                "audio_bytes": None,
            }

        try:
            # Get voice ID
            voice_id = self._get_voice_id(voice or "rachel")
            
            # Get model ID
            model_id = self.MODELS.get(model, model) if model else self.model
            
            # Build request
            url = f"{self.ELEVENLABS_TTS_URL}/{voice_id}"
            
            payload = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                    "use_speaker_boost": use_speaker_boost,
                }
            }
            
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            }

            logger.info(f"ElevenLabs TTS: model={model_id}, voice={voice_id}, text_length={len(text)}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    error_msg = f"ElevenLabs TTS API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "audio_base64": None,
                        "audio_bytes": None,
                    }

                # Response is audio bytes (MP3 by default)
                audio_bytes = response.content
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                
                logger.info(f"ElevenLabs TTS generated: {len(audio_bytes)} bytes")
                
                return {
                    "success": True,
                    "audio_base64": audio_base64,
                    "audio_bytes": audio_bytes,
                    "text": text,
                    "format": "mp3",
                    "voice": voice,
                    "model": model_id,
                }

        except Exception as exc:
            logger.error(f"ElevenLabs TTS failed: {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "audio_base64": None,
                "audio_bytes": None,
            }

    async def synthesize_pcm(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.8,
        style: float = 0.0,
    ) -> Dict[str, Any]:
        """Generate speech audio in PCM format for streaming to Twilio.
        
        ElevenLabs API returns MP3 by default, so we need to convert.
        For lower latency, we request PCM directly using output_format.
        
        Args:
            text: Text to convert to speech
            voice: Voice name or ID
            model: TTS model
            stability: Voice stability (0-1)
            similarity_boost: Voice clarity (0-1)
            style: Speaking style exaggeration (0-1)
        
        Returns:
            Dict with success 、audio_bytes (PCM format), and error fields
        """
        if not text:
            return {"success": False, "error": "No text provided"}

        if not self.api_key:
            return {"success": False, "error": "ElevenLabs API key not configured"}

        try:
            voice_id = self._get_voice_id(voice or "rachel")
            model_id = self.MODELS.get(model, model) if model else self.model
            
            # Request PCM format directly (24kHz, 16-bit signed little-endian)
            url = f"{self.ELEVENLABS_TTS_URL}/{voice_id}"
            
            # Add output_format query parameter for PCM
            # pcm_24000: 24kHz sample rate, 16-bit signed little-endian
            params = {"output_format": "pcm_24000"}
            
            payload = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                    "use_speaker_boost": True,
                }
            }
            
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    params=params,
                )
                
                if response.status_code != 200:
                    error_msg = f"ElevenLabs TTS PCM error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}

                pcm_bytes = response.content
                logger.info(f"ElevenLabs TTS PCM generated: {len(pcm_bytes)} bytes")
                
                return {
                    "success": True,
                    "audio_bytes": pcm_bytes,
                    "format": "pcm_24000",  # 24kHz, 16-bit signed LE
                }

        except Exception as exc:
            logger.error(f"ElevenLabs TTS PCM failed: {exc}", exc_info=True)
            return {"success": False, "error": str(exc)}

    async def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices from ElevenLabs API."""
        if not self.api_key:
            return []
            
        try:
            headers = {"xi-api-key": self.api_key}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.VOICES_URL, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("voices", [])
        except Exception as exc:
            logger.error(f"Failed to list ElevenLabs voices: {exc}")
        return []
