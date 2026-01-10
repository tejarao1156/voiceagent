import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/voiceagent")

# ============================================================================
# MONGODB CONFIGURATION (for conversation storage)
# ============================================================================
MONGODB_URL = os.getenv("MONGODB_URL", "")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "voiceagent")
MONGODB_CONVERSATIONS_COLLECTION = os.getenv("MONGODB_CONVERSATIONS_COLLECTION", "conversations")

# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================================================================
# ELEVENLABS CONFIGURATION
# ============================================================================
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# ============================================================================
# DEEPGRAM CONFIGURATION
# ============================================================================
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# ============================================================================
# HUGGING FACE CONFIGURATION
# ============================================================================
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")  # Optional - works without but better with it
HF_TOKEN = os.getenv("HF_TOKEN")  # Required for fal-ai provider

# ============================================================================
# VOICE PROCESSING CONFIGURATION
# ============================================================================
VOICE_MODEL = os.getenv("VOICE_MODEL", "whisper-1")
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")  # Use tts-1 for faster response (lower latency)
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

# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================
from utils.environment_detector import detect_runtime_environment, get_webhook_base_url

# Detect runtime environment (local, kubernetes, docker, unknown)
RUNTIME_ENVIRONMENT = detect_runtime_environment()

# ============================================================================
# TWILIO CONFIGURATION
# ============================================================================
# Note: Twilio credentials MUST be registered through the app UI.
# All credentials are stored in MongoDB via the "Register Phone Number" feature.
# No credentials should be set in .env file - they are pulled from MongoDB only.

# Get webhook base URL based on environment detection
# This will automatically use:
# - Explicit TWILIO_WEBHOOK_BASE_URL if set
# - Kubernetes ingress/service URL if in pod
# - ngrok URL if available locally
# - localhost fallback otherwise
TWILIO_WEBHOOK_BASE_URL = get_webhook_base_url()

# Determines how to process calls: "batch" for <Record>, "stream" for Media Streams.
TWILIO_PROCESSING_MODE = os.getenv("TWILIO_PROCESSING_MODE", "batch").lower()

# ============================================================================
# CAMPAIGN WORKER CONFIGURATION
# ============================================================================
# Voice campaigns: Heavy resource usage (streaming, memory, long-running calls)
# Use fewer concurrent workers to manage memory
CAMPAIGN_VOICE_WORKERS = int(os.getenv("CAMPAIGN_VOICE_WORKERS", "2"))
CAMPAIGN_VOICE_BATCH_SIZE = int(os.getenv("CAMPAIGN_VOICE_BATCH_SIZE", "2"))

# Message campaigns (SMS + WhatsApp): Lightweight, can handle many concurrent requests
# Both SMS and WhatsApp share the same settings
CAMPAIGN_MESSAGE_WORKERS = int(os.getenv("CAMPAIGN_MESSAGE_WORKERS", "50"))
CAMPAIGN_MESSAGE_BATCH_SIZE = int(os.getenv("CAMPAIGN_MESSAGE_BATCH_SIZE", "100"))

# General campaign worker settings
CAMPAIGN_POLL_INTERVAL = int(os.getenv("CAMPAIGN_POLL_INTERVAL", "5"))  # Seconds between queue checks

# Type-specific batch delays
# Voice: Uses webhook-based completion waiting, so minimal delay needed here
# Message (SMS/WhatsApp): Wait after sending batch
CAMPAIGN_VOICE_BATCH_DELAY = int(os.getenv("CAMPAIGN_VOICE_BATCH_DELAY", "1"))
CAMPAIGN_MESSAGE_BATCH_DELAY = int(os.getenv("CAMPAIGN_MESSAGE_BATCH_DELAY", "5"))

# Voice call completion timeout (max time to wait for a call to complete)
CAMPAIGN_VOICE_TIMEOUT = int(os.getenv("CAMPAIGN_VOICE_TIMEOUT", "300"))  # 5 minutes



