#!/usr/bin/env python3
"""
Create test audio file for STT testing
"""

import os
from dotenv import load_dotenv
from config import OPENAI_API_KEY

def create_test_audio():
    """Create a test audio file using TTS"""
    print("🎵 Creating test audio file for STT testing...")
    
    if not OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY not found")
        return False
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Create test text
        test_text = "Hello, this is a test of speech to text conversion. I am speaking into the microphone to test the API."
        print(f"📝 Test text: '{test_text}'")
        
        # Generate speech
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=test_text
        )
        
        # Save audio file
        audio_file_path = "test_stt_audio.wav"
        response.stream_to_file(audio_file_path)
        
        file_size = os.path.getsize(audio_file_path)
        print(f"✅ Test audio created: {audio_file_path} ({file_size} bytes)")
        print(f"💡 Use this file to test STT in Swagger!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test audio: {e}")
        return False

if __name__ == "__main__":
    load_dotenv()
    create_test_audio()
