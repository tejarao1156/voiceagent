import io
import wave
import audioop
import logging

logger = logging.getLogger(__name__)

def convert_pcm_to_mulaw(pcm_bytes: bytes, input_rate: int = 24000, input_width: int = 2) -> bytes:
    """
    Converts PCM audio bytes to 8kHz 8-bit mu-law format for Twilio.
    FAST conversion without ffmpeg - uses only Python's audioop.
    
    Args:
        pcm_bytes: Raw PCM audio bytes from OpenAI TTS (24kHz 16-bit by default)
        input_rate: Sample rate of input PCM (24000 for OpenAI)
        input_width: Sample width in bytes (2 = 16-bit)
    
    Returns:
        8kHz 8-bit mu-law audio bytes ready for Twilio
    """
    try:
        # Step 1: Resample from 24kHz to 8kHz (Twilio's required rate)
        # audioop.ratecv(fragment, width, nchannels, inrate, outrate, state)
        resampled_pcm, _ = audioop.ratecv(pcm_bytes, input_width, 1, input_rate, 8000, None)
        
        # Step 2: Convert 16-bit linear PCM to 8-bit mu-law
        mulaw_data = audioop.lin2ulaw(resampled_pcm, input_width)
        
        return mulaw_data
    except Exception as e:
        logger.error(f"Error converting PCM to mu-law: {e}", exc_info=True)
        return b''

def convert_mp3_to_mulaw(mp3_bytes: bytes) -> bytes:
    """
    Converts MP3 audio bytes to 8kHz 8-bit mu-law format for Twilio.
    LEGACY: Requires pydub + ffmpeg. Use convert_pcm_to_mulaw() for better performance.
    """
    try:
        from pydub import AudioSegment
        
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        
        # Resample to 8000 Hz and set to mono
        audio = audio.set_frame_rate(8000).set_channels(1)
        
        # Get raw 16-bit PCM data
        pcm_data = audio.raw_data
        
        # Convert 16-bit linear PCM to 8-bit mu-law
        mulaw_data = audioop.lin2ulaw(pcm_data, 2)
        
        return mulaw_data
    except Exception as e:
        logger.error(f"Error converting MP3 to mu-law: {e}", exc_info=True)
        return b''

def convert_mulaw_to_wav_bytes(mulaw_bytes: bytes, sample_rate: int = 8000, target_rate: int = 16000, boost_quiet: bool = True) -> bytes:
    """Converts raw mu-law audio bytes to WAV format bytes for STT.
    
    Optionally resamples to target_rate (16kHz recommended for ElevenLabs Scribe).
    Also applies audio boost for quiet speech to improve STT accuracy.
    """
    try:
        # Convert 8-bit mu-law to 16-bit linear PCM
        pcm_data = audioop.ulaw2lin(mulaw_bytes, 2)
        
        # Resample to target rate if different (8kHz → 16kHz for better STT accuracy)
        if target_rate != sample_rate:
            pcm_data, _ = audioop.ratecv(pcm_data, 2, 1, sample_rate, target_rate, None)
            output_rate = target_rate
            logger.debug(f"Resampled audio from {sample_rate}Hz to {target_rate}Hz for better STT accuracy")
        else:
            output_rate = sample_rate
        
        # Apply audio boost for quiet speech (helps STT understand soft speakers)
        if boost_quiet:
            rms_before = audioop.rms(pcm_data, 2)
            # Only boost if RMS is below threshold (quiet audio)
            if rms_before > 0 and rms_before < 1000:
                # Calculate boost factor (target RMS ~2500, cap at 4x)
                boost_factor = min(2500 / rms_before, 4.0)
                pcm_data = audioop.mul(pcm_data, 2, boost_factor)
                # Clipping protection
                max_val = audioop.max(pcm_data, 2)
                if max_val > 32000:
                    safe_factor = 32000 / max_val
                    pcm_data = audioop.mul(pcm_data, 2, safe_factor)
                logger.info(f"🔊 Boosted quiet audio for STT: RMS {rms_before} → {audioop.rms(pcm_data, 2)} (factor: {boost_factor:.1f}x)")
        
        # Create a WAV file in memory
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(output_rate)
            wf.writeframes(pcm_data)
        
        wav_io.seek(0)
        return wav_io.read()
    except Exception as e:
        logger.error(f"Error converting mu-law to WAV: {e}", exc_info=True)
        return b''

def normalize_audio(pcm_data: bytes, width: int = 2, target_level: float = 0.9) -> bytes:
    """Normalize audio levels to prevent clipping and improve STT accuracy.
    
    Args:
        pcm_data: Raw PCM audio bytes
        width: Sample width in bytes (2 = 16-bit)
        target_level: Target level (0.9 = 90% of max to avoid clipping)
    
    Returns:
        Normalized PCM audio bytes
    """
    try:
        max_val = audioop.max(pcm_data, width)
        if max_val > 0:
            factor = (32767 * target_level) / max_val
            return audioop.mul(pcm_data, width, factor)
        return pcm_data
    except Exception as e:
        logger.error(f"Error normalizing audio: {e}", exc_info=True)
        return pcm_data

def boost_quiet_audio(pcm_data: bytes, width: int = 2, target_rms: int = 2000, min_rms: int = 500) -> bytes:
    """Boost quiet audio to improve STT accuracy for soft/quiet speakers.
    
    Per ElevenLabs VAD best practices: boost low-volume audio before STT to help
    the speech recognition model understand quiet speech better.
    
    Args:
        pcm_data: Raw PCM audio bytes
        width: Sample width in bytes (2 = 16-bit)
        target_rms: Target RMS level to boost to (default 2000)
        min_rms: Minimum RMS below which to apply boost
    
    Returns:
        Boosted PCM audio bytes (or original if already loud enough)
    """
    try:
        rms = audioop.rms(pcm_data, width)
        
        # Only boost if audio is quiet (below min_rms threshold)
        if rms > 0 and rms < min_rms:
            # Calculate boost factor needed to reach target RMS
            # Cap at 4x to avoid excessive amplification and clipping
            boost_factor = min(target_rms / rms, 4.0)
            
            # Apply gain boost
            boosted = audioop.mul(pcm_data, width, boost_factor)
            
            # Verify we didn't clip (max value should be < 32767)
            max_val = audioop.max(boosted, width)
            if max_val > 32000:
                # Reduce boost to avoid clipping
                safe_factor = (32000 / max_val) * boost_factor
                boosted = audioop.mul(pcm_data, width, safe_factor)
                logger.debug(f"Boosted quiet audio with clipping protection: RMS {rms} → {audioop.rms(boosted, width)} (factor: {safe_factor:.1f})")
            else:
                logger.debug(f"Boosted quiet audio: RMS {rms} → {audioop.rms(boosted, width)} (factor: {boost_factor:.1f})")
            
            return boosted
        
        return pcm_data
    except Exception as e:
        logger.warning(f"Error boosting audio: {e}")
        return pcm_data

def apply_noise_gate(pcm_data: bytes, threshold: int = 300, width: int = 2) -> bytes:
    """Apply noise gate to reduce background noise for better STT.
    
    Samples below threshold are reduced (not zeroed) to preserve natural sound.
    
    Args:
        pcm_data: Raw PCM audio bytes
        threshold: RMS threshold below which to gate
        width: Sample width in bytes
    
    Returns:
        Gated PCM audio bytes
    """
    try:
        import struct
        # Check overall RMS - if signal is strong, don't gate
        rms = audioop.rms(pcm_data, width)
        if rms > threshold * 2:
            return pcm_data  # Strong signal, no gating needed
        
        # Apply soft gating by reducing low-level samples
        samples = struct.unpack(f'{len(pcm_data)//width}h', pcm_data)
        gated = []
        for s in samples:
            if abs(s) < threshold:
                gated.append(s // 4)  # Reduce but don't zero
            else:
                gated.append(s)
        return struct.pack(f'{len(gated)}h', *gated)
    except Exception as e:
        logger.error(f"Error applying noise gate: {e}", exc_info=True)
        return pcm_data
