"""Text-to-speech tool using Hugging Face Kokoro-82M model locally."""

from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from kokoro_tts import Kokoro
    import soundfile as sf
    HAS_KOKORO = True
except ImportError:
    HAS_KOKORO = False

# HF_TOKEN not needed for local model, but kept for potential future use


logger = logging.getLogger(__name__)


class TextToSpeechTool:
    """Tool responsible for converting text into playable audio using Kokoro-82M locally."""

    def __init__(self, client: Optional[Any] = None) -> None:
        self.model_id = "hexgrad/Kokoro-82M"
        self.kokoro = None
        self._initialized = False
        
        # Get the models directory path
        current_dir = Path(__file__).parent.parent.parent.parent  # Go up to voiceagent root
        self.models_dir = current_dir / "models"
        self.model_path = self.models_dir / "kokoro-v1.0.onnx"
        self.voices_path = self.models_dir / "voices-v1.0.bin"
        
    def _initialize_model(self):
        """Initialize the Kokoro TTS model."""
        if self._initialized:
            return
            
        if not HAS_KOKORO:
            raise ImportError(
                "kokoro_tts library is required for local TTS. "
                "Install with: pip install kokoro-tts"
            )
        
        if not self.model_path.exists() or not self.voices_path.exists():
            raise FileNotFoundError(
                f"Model files not found. Expected:\n"
                f"  - {self.model_path}\n"
                f"  - {self.voices_path}\n"
                f"Please download them from: "
                f"https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/"
            )
        
        try:
            logger.info(f"Loading Kokoro-82M model locally: {self.model_id}")
            logger.info("This may take a moment on first run...")
            
            # Initialize Kokoro with model files
            self.kokoro = Kokoro(
                model_path=str(self.model_path),
                voices_path=str(self.voices_path)
            )
            
            # Get available voices to use default
            voices = self.kokoro.get_voices()
            self.default_voice = list(voices.keys())[0] if isinstance(voices, dict) and voices else None
            
            self._initialized = True
            logger.info(f"Successfully loaded TTS model: {self.model_id}")
            if self.default_voice:
                logger.info(f"Default voice: {self.default_voice}")
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        *,
        persona: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate speech audio for the provided text using Kokoro-82M locally."""
        if not text:
            return {
                "success": False,
                "error": "Text is required for synthesis.",
                "audio_base64": None,
                "audio_bytes": None,
            }

        if not HAS_KOKORO:
            return {
                "success": False,
                "error": "kokoro_tts library is required for local TTS. Install with: pip install kokoro-tts",
                "audio_base64": None,
                "audio_bytes": None,
            }

        try:
            # Initialize model if not already done
            if not self._initialized:
                self._initialize_model()
            
            # Generate audio
            logger.info(f"Generating speech for: {text[:80]}")
            
            # Get available voices
            available_voices = self.kokoro.get_voices()
            
            # Map persona voices to Kokoro voices if provided, otherwise use default
            # Kokoro voices are like: af_bella, af_sky, en_aj, en_anna, etc.
            if voice and voice in available_voices:
                selected_voice = voice
            else:
                # Use default voice (first available)
                if isinstance(available_voices, dict):
                    selected_voice = list(available_voices.keys())[0]
                else:
                    # Try common Kokoro voice names
                    for v in ['af_bella', 'en_aj', 'en_anna', 'en_sarah']:
                        if v in available_voices:
                            selected_voice = v
                            break
                    else:
                        selected_voice = list(available_voices.keys())[0] if available_voices else 'af_bella'
            
            logger.info(f"Using voice: {selected_voice}")
            
            # Generate speech using Kokoro.create()
            # Returns (audio_array, sample_rate)
            audio_array, sample_rate = self.kokoro.create(
                text=text,
                voice=selected_voice,
                lang='en-us',
                speed=1.0
            )
            
            # Convert numpy array to audio bytes (WAV format)
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, audio_array, sample_rate, format="WAV")
            audio_bytes = audio_buffer.getvalue()
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            
            logger.info(f"Text-to-speech generated successfully for: {text[:80]}")
            return {
                "success": True,
                "audio_base64": audio_base64,
                "audio_bytes": audio_bytes,
                "text": text,
                "format": "wav",
                "voice": selected_voice,
                "model": self.model_id,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Text-to-speech failed: {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "audio_base64": None,
                "audio_bytes": None,
            }
