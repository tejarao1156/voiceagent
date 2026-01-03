"""Unit tests for Deepgram STT/TTS integration."""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDeepgramSTT:
    """Tests for DeepgramSpeechToTextTool."""
    
    def test_import(self):
        """Test that the module can be imported."""
        from tools.understanding.speech_to_text.deepgram_stt import DeepgramSpeechToTextTool
        assert DeepgramSpeechToTextTool is not None
    
    def test_instantiation_without_key(self):
        """Test instantiation without API key logs warning."""
        import os
        original_key = os.environ.get('DEEPGRAM_API_KEY')
        os.environ['DEEPGRAM_API_KEY'] = ''
        
        from tools.understanding.speech_to_text.deepgram_stt import DeepgramSpeechToTextTool
        tool = DeepgramSpeechToTextTool(api_key=None)
        
        # Restore
        if original_key:
            os.environ['DEEPGRAM_API_KEY'] = original_key
        
        # Client should be None when no API key
        assert tool.client is None
    
    def test_supported_models(self):
        """Test that supported models are defined."""
        from tools.understanding.speech_to_text.deepgram_stt import DeepgramSpeechToTextTool
        models = DeepgramSpeechToTextTool.get_supported_models()
        
        assert "nova-2" in models
        assert "nova-3" in models
        assert "base" in models
        assert "enhanced" in models
    
    def test_supported_languages(self):
        """Test that supported languages are defined."""
        from tools.understanding.speech_to_text.deepgram_stt import DeepgramSpeechToTextTool
        languages = DeepgramSpeechToTextTool.get_supported_languages()
        
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
    
    def test_transcribe_sync_no_client(self):
        """Test transcribe_sync returns error when client not initialized."""
        from tools.understanding.speech_to_text.deepgram_stt import DeepgramSpeechToTextTool
        
        tool = DeepgramSpeechToTextTool(api_key=None)
        result = tool.transcribe_sync(b"fake audio data")
        
        assert result["text"] == ""
        assert "error" in result


class TestDeepgramTTS:
    """Tests for DeepgramTextToSpeechTool."""
    
    def test_import(self):
        """Test that the module can be imported."""
        from tools.response.text_to_speech.deepgram_tts import DeepgramTextToSpeechTool
        assert DeepgramTextToSpeechTool is not None
    
    def test_instantiation_without_key(self):
        """Test instantiation without API key logs warning."""
        from tools.response.text_to_speech.deepgram_tts import DeepgramTextToSpeechTool
        tool = DeepgramTextToSpeechTool(api_key=None)
        
        # Client should be None when no API key
        assert tool.client is None
    
    def test_available_voices(self):
        """Test that Aura voices are defined."""
        from tools.response.text_to_speech.deepgram_tts import DeepgramTextToSpeechTool
        voices = DeepgramTextToSpeechTool.get_available_voices()
        
        assert "asteria" in voices
        assert "orion" in voices
        assert "luna" in voices
        assert "zeus" in voices
    
    def test_list_voices(self):
        """Test voice list format for UI dropdowns."""
        from tools.response.text_to_speech.deepgram_tts import DeepgramTextToSpeechTool
        voices = DeepgramTextToSpeechTool.list_voices()
        
        assert len(voices) > 0
        assert all("id" in v and "name" in v for v in voices)
        assert any("aura-asteria-en" in v["id"] for v in voices)
    
    def test_model_name_conversion(self):
        """Test voice name to model name conversion."""
        from tools.response.text_to_speech.deepgram_tts import DeepgramTextToSpeechTool
        tool = DeepgramTextToSpeechTool(api_key=None)
        
        # Short name -> full model
        assert tool._get_model_name("asteria") == "aura-asteria-en"
        assert tool._get_model_name("orion") == "aura-orion-en"
        
        # Full name -> unchanged
        assert tool._get_model_name("aura-asteria-en") == "aura-asteria-en"
    
    def test_synthesize_pcm_no_client(self):
        """Test synthesize_pcm returns empty when client not initialized."""
        from tools.response.text_to_speech.deepgram_tts import DeepgramTextToSpeechTool
        
        tool = DeepgramTextToSpeechTool(api_key=None)
        result = tool.synthesize_pcm("Hello world")
        
        assert result == b""


class TestProviderFactory:
    """Tests for provider factory routing."""
    
    def test_import(self):
        """Test that provider factory can be imported."""
        from tools.provider_factory import get_stt_tool, get_tts_tool
        assert get_stt_tool is not None
        assert get_tts_tool is not None
    
    def test_stt_routing_deepgram(self):
        """Test STT routes to Deepgram for nova models."""
        from tools.provider_factory import get_stt_tool, is_deepgram_stt
        
        assert is_deepgram_stt("nova-2") == True
        assert is_deepgram_stt("nova-3") == True
        assert is_deepgram_stt("deepgram-nova-2") == True
        assert is_deepgram_stt("whisper-1") == False
    
    def test_tts_routing_deepgram(self):
        """Test TTS routes to Deepgram for aura models."""
        from tools.provider_factory import get_tts_tool, is_deepgram_tts
        
        assert is_deepgram_tts("aura-asteria-en") == True
        assert is_deepgram_tts("deepgram-aura") == True
        assert is_deepgram_tts("tts-1") == False
        assert is_deepgram_tts("eleven_turbo_v2_5") == False
    
    def test_default_params(self):
        """Test default parameter retrieval."""
        from tools.provider_factory import get_default_stt_params, get_default_tts_params
        
        deepgram_stt = get_default_stt_params("deepgram")
        assert deepgram_stt["model"] == "nova-2"
        assert deepgram_stt["smart_format"] == True
        
        deepgram_tts = get_default_tts_params("deepgram")
        assert deepgram_tts["model"] == "aura-asteria-en"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
