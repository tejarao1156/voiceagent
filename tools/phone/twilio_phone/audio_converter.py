"""Audio format conversion utilities for Twilio Media Streams.

Twilio Media Streams use μ-law PCM audio at 8000Hz sample rate.
OpenAI Whisper expects higher quality audio (typically 16000Hz+ WAV format).
This module handles conversion between these formats.
"""

from __future__ import annotations

import audioop
import io
import logging
import struct
from typing import Optional

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

logger = logging.getLogger(__name__)


def twilio_to_wav(audio_data: bytes, sample_rate: int = 8000) -> bytes:
    """
    Convert Twilio μ-law PCM audio to WAV format for OpenAI Whisper.
    
    Args:
        audio_data: Raw μ-law PCM audio bytes from Twilio
        sample_rate: Source sample rate (default 8000Hz for Twilio)
    
    Returns:
        WAV format audio bytes suitable for OpenAI Whisper
    """
    if not audio_data:
        raise ValueError("Empty audio data provided")
    
    try:
        # Convert μ-law to linear PCM (16-bit)
        linear_pcm = audioop.ulaw2lin(audio_data, 2)
        
        # Resample to 16000Hz if needed (OpenAI Whisper prefers 16kHz+)
        target_sample_rate = 16000
        if sample_rate != target_sample_rate:
            # Simple linear resampling (for better quality, use pydub if available)
            if HAS_PYDUB:
                # Create AudioSegment from raw PCM
                audio_segment = AudioSegment(
                    linear_pcm,
                    frame_rate=sample_rate,
                    sample_width=2,
                    channels=1
                )
                # Resample to target rate
                audio_segment = audio_segment.set_frame_rate(target_sample_rate)
                linear_pcm = audio_segment.raw_data
                sample_rate = target_sample_rate
            else:
                # Basic resampling: duplicate samples (simple but works)
                ratio = target_sample_rate / sample_rate
                if ratio > 1:
                    # Upsample by repeating samples
                    linear_pcm = audioop.ratecv(
                        linear_pcm, 2, 1, sample_rate, target_sample_rate, None
                    )[0]
                else:
                    # Downsample by skipping samples
                    linear_pcm = audioop.ratecv(
                        linear_pcm, 2, 1, sample_rate, target_sample_rate, None
                    )[0]
                sample_rate = target_sample_rate
        
        # Create WAV file header
        num_samples = len(linear_pcm) // 2  # 2 bytes per sample (16-bit)
        wav_header = _create_wav_header(num_samples, sample_rate, channels=1, bits_per_sample=16)
        
        # Combine header and PCM data
        wav_data = wav_header + linear_pcm
        
        logger.debug(f"Converted Twilio audio: {len(audio_data)} bytes → {len(wav_data)} bytes WAV")
        return wav_data
        
    except Exception as e:
        logger.error(f"Error converting Twilio audio to WAV: {e}")
        raise ValueError(f"Audio conversion failed: {str(e)}")


def wav_to_twilio(audio_data: bytes, sample_rate: int = 16000) -> bytes:
    """
    Convert WAV/MP3 audio to Twilio μ-law PCM format.
    
    Args:
        audio_data: WAV or MP3 audio bytes
        sample_rate: Source sample rate (default 16000Hz)
    
    Returns:
        μ-law PCM audio bytes suitable for Twilio Media Stream
    """
    if not audio_data:
        raise ValueError("Empty audio data provided")
    
    try:
        # If pydub is available, use it for better format handling
        if HAS_PYDUB:
            # Load audio (handles WAV, MP3, etc.)
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Convert to mono if needed
            if audio_segment.channels > 1:
                audio_segment = audio_segment.set_channels(1)
            
            # Resample to 8000Hz (Twilio requirement)
            audio_segment = audio_segment.set_frame_rate(8000)
            
            # Get raw PCM data (16-bit)
            pcm_data = audio_segment.raw_data
            
            # Convert linear PCM to μ-law
            mulaw_data = audioop.lin2ulaw(pcm_data, 2)
            
            logger.debug(f"Converted audio to Twilio: {len(audio_data)} bytes → {len(mulaw_data)} bytes μ-law")
            return mulaw_data
        else:
            # Fallback: assume it's already WAV format
            # Extract PCM data from WAV (skip header)
            # Simple approach: try to find data chunk
            if audio_data[:4] == b'RIFF':
                # WAV file - find data chunk
                data_start = audio_data.find(b'data') + 8
                if data_start > 8:
                    pcm_data = audio_data[data_start:]
                else:
                    pcm_data = audio_data[44:]  # Standard WAV header size
            else:
                pcm_data = audio_data  # Assume raw PCM
            
            # Resample to 8000Hz if needed
            if sample_rate != 8000:
                pcm_data = audioop.ratecv(pcm_data, 2, 1, sample_rate, 8000, None)[0]
            
            # Convert to μ-law
            mulaw_data = audioop.lin2ulaw(pcm_data, 2)
            
            return mulaw_data
            
    except Exception as e:
        logger.error(f"Error converting audio to Twilio format: {e}")
        raise ValueError(f"Audio conversion failed: {str(e)}")


def _create_wav_header(num_samples: int, sample_rate: int, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """Create a WAV file header."""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = num_samples * block_align
    file_size = 36 + data_size
    
    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        file_size,
        b'WAVE',
        b'fmt ',
        16,  # fmt chunk size
        1,   # audio format (PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size
    )
    
    return header

