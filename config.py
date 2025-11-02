import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/voiceagent")

# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================================================================
# VOICE PROCESSING CONFIGURATION
# ============================================================================
VOICE_MODEL = os.getenv("VOICE_MODEL", "whisper-1")
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1-hd")
INFERENCE_MODEL = os.getenv("INFERENCE_MODEL", "gpt-4o-mini")

# ============================================================================
# API CONFIGURATION
# ============================================================================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "4002"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
RELOAD = os.getenv("RELOAD", "True").lower() == "true"

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")

# ============================================================================
# CORS CONFIGURATION
# ============================================================================
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# ============================================================================
# FEATURE FLAGS
# ============================================================================
ENABLE_VOICE_PROCESSING = os.getenv("ENABLE_VOICE_PROCESSING", "True").lower() == "true"
ENABLE_CONVERSATION_MANAGEMENT = os.getenv("ENABLE_CONVERSATION_MANAGEMENT", "True").lower() == "true"

# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================
MAX_AUDIO_FILE_SIZE = int(os.getenv("MAX_AUDIO_FILE_SIZE", "10485760"))  # 10MB
ALLOWED_AUDIO_FORMATS = os.getenv("ALLOWED_AUDIO_FORMATS", "wav,mp3,m4a,flac,webm").split(",")

# ============================================================================
# CONVERSATION CONFIGURATION
# ============================================================================
MAX_CONVERSATION_LENGTH = int(os.getenv("MAX_CONVERSATION_LENGTH", "50"))
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# ============================================================================
# SUPABASE CONFIGURATION
# ============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
