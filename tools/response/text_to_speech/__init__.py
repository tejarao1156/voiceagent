"""Text-to-speech tool using OpenAI TTS API."""

from __future__ import annotations

import base64
import logging
import re
import asyncio
import io
from typing import Any, Dict, Optional, List

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

from config import OPENAI_API_KEY, TTS_MODEL

logger = logging.getLogger(__name__)


class TextToSpeechTool:
    """Tool responsible for converting text into playable audio using OpenAI TTS."""

    def __init__(self, client: Optional[Any] = None) -> None:
        self.client = client
        if not self.client and HAS_OPENAI and OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = TTS_MODEL or "tts-1"  # Default to faster model for lower latency
        # OpenAI TTS available voices
        self.available_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for parallel processing."""
        # Fast split by sentence endings
        sentences = re.split(r'([.!?]+)', text)
        result = []
        current = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Combine shorter sentences (up to 300 chars per chunk for better parallelization)
            if len(current) + len(sentence) < 300 and current:
                current += " " + sentence
            else:
                if current:
                    result.append(current)
                current = sentence
        
        if current:
            result.append(current)
        
        # If no sentences found or only one, return whole text
        if not result:
            return [text]
        if len(result) == 1:
            return result
        
        return result

    async def _synthesize_chunk(self, text: str, voice: str, model: Optional[str] = None) -> bytes:
        """Synthesize a single text chunk."""
        try:
            # Use provided model or fall back to instance default
            tts_model = model or self.model
            response = self.client.audio.speech.create(
                model=tts_model,
                voice=voice,
                input=text,
                response_format="mp3"
            )
            return response.content
        except Exception as e:
            logger.error(f"TTS chunk failed: {e}")
            raise

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        *,
        persona: Optional[Dict[str, Any]] = None,
        parallel: bool = False,  # Disable parallel by default for faster response (most texts are short)
        model: Optional[str] = None  # Optional TTS model override (e.g., "tts-1", "tts-1-hd")
    ) -> Dict[str, Any]:
        """Generate speech audio for the provided text using OpenAI TTS.
        
        For longer texts, splits into sentences and processes in parallel for faster output.
        """
        if not text:
            return {
                "success": False,
                "error": "Text is required for synthesis.",
                "audio_base64": None,
                "audio_bytes": None,
            }

        if not HAS_OPENAI:
            return {
                "success": False,
                "error": "OpenAI library is required. Install with: pip install openai",
                "audio_base64": None,
                "audio_bytes": None,
            }

        if not OPENAI_API_KEY:
            return {
                "success": False,
                "error": "OPENAI_API_KEY is not configured in environment variables.",
                "audio_base64": None,
                "audio_bytes": None,
            }

        if not self.client:
            return {
                "success": False,
                "error": "OpenAI client not initialized. Check OPENAI_API_KEY configuration.",
                "audio_base64": None,
                "audio_bytes": None,
            }

        try:
            # Select voice
            if persona and persona.get("tts_voice"):
                selected_voice = persona.get("tts_voice")
            elif voice and voice in self.available_voices:
                selected_voice = voice
            else:
                selected_voice = self.available_voices[0]

            # Map persona voices to OpenAI voices if needed
            if selected_voice not in self.available_voices:
                voice_mapping = {
                    "verse": "nova", "sol": "shimmer",
                    "alloy": "alloy", "echo": "echo", "fable": "fable",
                    "onyx": "onyx", "nova": "nova", "shimmer": "shimmer",
                }
                selected_voice = voice_mapping.get(selected_voice.lower(), self.available_voices[0])

            # Use provided model or fall back to instance default
            tts_model = model or self.model
            
            logger.info(f"Generating speech: model={tts_model}, voice={selected_voice}, text_length={len(text)}")

            # For short texts (< 200 chars), process directly (faster - no chunking overhead)
            # For longer texts, split and process in parallel
            if len(text) < 200 or not parallel:
                # Single TTS call for short/medium text (fastest for most responses)
                response = self.client.audio.speech.create(
                    model=tts_model,
                    voice=selected_voice,
                    input=text,
                    response_format="mp3"
                )
                audio_bytes = response.content
            else:
                # Split into sentences and process in parallel
                sentences = self._split_into_sentences(text)
                logger.info(f"Processing {len(sentences)} sentence chunks in parallel")
                
                # Process all chunks in parallel
                tasks = [self._synthesize_chunk(sentence, selected_voice, tts_model) for sentence in sentences]
                audio_chunks = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Combine audio chunks (skip failed ones)
                audio_bytes_list = []
                for i, chunk in enumerate(audio_chunks):
                    if isinstance(chunk, Exception):
                        logger.warning(f"Chunk {i} failed: {chunk}")
                        continue
                    audio_bytes_list.append(chunk)
                
                if not audio_bytes_list:
                    raise Exception("All TTS chunks failed")
                
                # Combine MP3 chunks properly using pydub if available
                if HAS_PYDUB and len(audio_bytes_list) > 1:
                    # Combine MP3 segments properly
                    combined = AudioSegment.empty()
                    for chunk_bytes in audio_bytes_list:
                        chunk_audio = AudioSegment.from_mp3(io.BytesIO(chunk_bytes))
                        combined += chunk_audio
                    
                    # Export as MP3
                    output = io.BytesIO()
                    combined.export(output, format="mp3")
                    audio_bytes = output.getvalue()
                else:
                    # Fallback: simple concatenation (works for MP3 but may have slight gaps)
                    audio_bytes = b''.join(audio_bytes_list)

            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            logger.info(f"Text-to-speech generated: {len(audio_bytes)} bytes")
            
            return {
                "success": True,
                "audio_base64": audio_base64,
                "audio_bytes": audio_bytes,
                "text": text,
                "format": "mp3",
                "voice": selected_voice,
                "model": self.model,
            }
        except Exception as exc:
            logger.error(f"Text-to-speech failed: {exc}", exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "audio_base64": None,
                "audio_bytes": None,
            }
