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

def convert_mulaw_to_wav_bytes(mulaw_bytes: bytes, sample_rate: int = 8000) -> bytes:
    """Converts raw mu-law audio bytes to WAV format bytes for Whisper STT."""
    try:
        # Convert 8-bit mu-law to 16-bit linear PCM
        pcm_data = audioop.ulaw2lin(mulaw_bytes, 2)
        
        # Create a WAV file in memory
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        
        wav_io.seek(0)
        return wav_io.read()
    except Exception as e:
        logger.error(f"Error converting mu-law to WAV: {e}", exc_info=True)
        return b''
