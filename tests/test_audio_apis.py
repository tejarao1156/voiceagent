import sys
import os
import base64
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import api_general
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_general import app

client = TestClient(app)

def test_convert_to_wav():
    # Create 20ms of silence in mu-law (0xFF is silence in mu-law)
    # 8000Hz * 0.02s = 160 samples
    silence_mulaw = b'\xff' * 160
    b64_input = base64.b64encode(silence_mulaw).decode('utf-8')
    
    response = client.post(
        "/api/test/audio/convert-to-wav",
        json={"audio_data": b64_input}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "wav_base64" in data
    
    # Check if output is WAV
    wav_bytes = base64.b64decode(data["wav_base64"])
    assert wav_bytes.startswith(b'RIFF')
    assert b'WAVE' in wav_bytes

def test_convert_to_mulaw():
    # Create a minimal WAV file (silence)
    # Header + 160 samples of silence (0x0000 in 16-bit PCM)
    # We can use the output from the previous test or construct one
    
    # Let's use the API to get a valid WAV first
    silence_mulaw = b'\xff' * 160
    b64_input = base64.b64encode(silence_mulaw).decode('utf-8')
    wav_resp = client.post(
        "/api/test/audio/convert-to-wav",
        json={"audio_data": b64_input}
    )
    wav_b64 = wav_resp.json()["wav_base64"]
    
    # Now convert back
    response = client.post(
        "/api/test/audio/convert-to-mulaw",
        json={"audio_data": wav_b64}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "mulaw_base64" in data
    
    # Check size (should be close to original 160 bytes)
    mulaw_bytes = base64.b64decode(data["mulaw_base64"])
    # Note: Resampling/conversion might change size slightly depending on implementation
    # But for silence it should be close
    assert len(mulaw_bytes) > 0

def test_vad_detect_silence():
    # 20ms of silence (0xFF in mu-law)
    silence_mulaw = b'\xff' * 160
    b64_input = base64.b64encode(silence_mulaw).decode('utf-8')
    
    response = client.post(
        "/api/test/audio/vad-detect",
        json={"audio_data": b64_input, "sample_rate": 8000}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_speech"] is False

def test_vad_detect_speech_simulation():
    # It's hard to simulate speech with random bytes, but we can try
    # Random bytes usually trigger VAD as noise/speech
    import random
    random_bytes = bytes([random.randint(0, 255) for _ in range(160)])
    b64_input = base64.b64encode(random_bytes).decode('utf-8')
    
    response = client.post(
        "/api/test/audio/vad-detect",
        json={"audio_data": b64_input, "sample_rate": 8000}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # We don't assert is_speech because random noise might or might not trigger it
    # But the call should succeed
