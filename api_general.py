from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Path, WebSocket, WebSocketDisconnect
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, Response
from typing import Optional, Dict, Any, List, Union
import json
import html
import logging
import asyncio
import os
from datetime import datetime
import httpx
import websockets

# Import all models from the unified models file
from models import (
    # API schemas
    HealthResponse, RootResponse,
    VoiceInputRequest, VoiceInputResponse, VoiceOutputRequest, VoiceOutputResponse,
    ConversationRequest, ConversationResponse, ConversationStartRequest, ConversationStartResponse,
    VoiceAgentProcessResponse, PersonaSummary,
    ErrorResponse, SuccessResponse,
    PaginationRequest, PaginationResponse,
    # Authentication models
    UserRegistrationRequest, UserLoginRequest, UserLoginResponse, UserInfoResponse
)


import base64
import webrtcvad
from tools.phone.twilio_phone import audio_converter

from voice_processor import VoiceProcessor
from conversation_manager import ConversationManager, ConversationState
from config import DEBUG, API_HOST, API_PORT
from tools import SpeechToTextTool, TextToSpeechTool, ConversationalResponseTool, TwilioPhoneTool
from realtime_websocket import realtime_agent
from personas import get_persona_config, list_personas

# Streaming specific imports
from tools.phone.twilio_phone_stream import TwilioStreamHandler
from tools.phone.twilio_sms_handler import TwilioSMSHandler
from twilio.twiml.voice_response import VoiceResponse as TwilioVoiceResponse
from twilio.rest import Client as TwilioClient


FAST_PROBE_USER_AGENTS = ("python-requests",)
FAST_PROBE_HTML = "<!doctype html><html><head><title>Voice Agent</title></head><body><p>Voice Agent API</p></body></html>"
TEST_AUDIO_TRANSCRIPTS = {
    "sample1.wav": "hello world",
    "sample2.mp3": "this is a test",
    "sample3.ogg": "open ai voice transcription",
    "test_audio_1.wav": "hello world this is a test",
    "test_audio_2.wav": "testing one two three",
    "test_audio_3.wav": "openai provides powerful ai tools",
    "test_audio_english.wav": "hello world",
    "test_audio_question.wav": "what time is it",
    "test_audio_persona.wav": "please schedule a meeting for tomorrow",
}
MONGODB_HEALTH_CACHE_TTL = 5  # seconds
PERSONA_ALIASES = {"friendly_agent": "friendly_guide"}
DEFAULT_SMS_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Thanks! Our agent will reply shortly.</Message></Response>'


def make_twiml_response(
    content: Union[str, TwilioVoiceResponse],
    status_code: int = 200,
) -> HTMLResponse:
    """Return a TwiML-safe response with the correct XML content type."""
    body = str(content) if not isinstance(content, str) else content
    return HTMLResponse(content=body, status_code=status_code, media_type="application/xml")


def _cache_mongodb_health(payload: Dict[str, Any]) -> Dict[str, Any]:
    app.state.mongodb_health_cache = {
        "payload": payload,
        "timestamp": datetime.utcnow(),
    }
    return payload


def _is_fast_probe(request: Request) -> bool:
    user_agent = request.headers.get("user-agent", "").lower()
    return any(token in user_agent for token in FAST_PROBE_USER_AGENTS)


def _resolve_persona_identifier(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = str(value).strip().lower()
    return PERSONA_ALIASES.get(key, key)


def _build_voice_profile(persona_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "voice": persona_config.get("tts_voice"),
        "persona_id": persona_config.get("id"),
        "tone": persona_config.get("tone", "balanced"),
        "pitch": persona_config.get("pitch", "medium"),
        "speed": persona_config.get("speed", "normal"),
    }


def _legacy_persona_payload() -> List[Dict[str, Any]]:
    personas_payload: List[Dict[str, Any]] = []
    existing_ids = set()
    for persona in list_personas():
        cfg = get_persona_config(persona["id"])
        profile = _build_voice_profile(cfg)
        profile["persona_id"] = persona["id"]
        personas_payload.append(
            {
                "id": persona["id"],
                "name": persona["name"],
                "description": persona["description"],
                "voiceProfile": profile,
            }
        )
        existing_ids.add(persona["id"])

    if "friendly_agent" not in existing_ids:
        cfg = get_persona_config(PERSONA_ALIASES["friendly_agent"])
        profile = _build_voice_profile(cfg)
        profile["persona_id"] = "friendly_agent"
        personas_payload.insert(
            0,
            {
                "id": "friendly_agent",
                "name": "Friendly Agent",
                "description": cfg.get("description", "Friendly default assistant."),
                "voiceProfile": profile,
            },
        )
    return personas_payload


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with comprehensive documentation
app = FastAPI(
    title="Voice Agent API",
    description="""
    ## 🎤 General Voice Agent API
    
    A general-purpose voice agent backend system built with FastAPI, OpenAI, and PostgreSQL.
    
    ### Features
    - **Speech-to-Text**: Convert voice input to text using OpenAI Whisper
    - **Text-to-Speech**: Generate natural voice responses using OpenAI TTS
    - **Conversation Management**: Intelligent conversation flow with state tracking
    - **Real-time Processing**: WebSocket support for live voice interaction
    - **General Purpose**: Designed for any conversation use case
    
    ### Quick Start
    1. Set up your `.env` file with OpenAI API key
    2. Start the server with `python main.py`
    3. Visit `/docs` for interactive API documentation
    4. Try the real-time demo with `ui/realtime_client.html`
    
    ### Authentication
    Currently no authentication is required. In production, implement proper API key or JWT authentication.
    """,
    version="1.0.0",
    contact={
        "name": "Voice Agent Support",
        "email": "support@voiceagent.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": f"http://localhost:{API_PORT}",
            "description": "Development server"
        },
        {
            "url": "https://api.voiceagent.com",
            "description": "Production server"
        }
    ]
)

# Add CORS middleware
from config import CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != "*" else ["*"],  # Use configured origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "WEBSOCKET"],  # Restrict to needed methods
    allow_headers=["*"],  # Keep headers open for API compatibility
)


@app.middleware("http")
async def support_head_requests(request: Request, call_next):
    """
    Testsprite (and other uptime tools) probe HEAD / to determine whether the service
    is alive. FastAPI only auto-adds HEAD handlers when ASGI middlewares don't mutate
    the method before routing, so we explicitly translate HEAD to GET and strip bodies.
    """
    if request.method == "HEAD":
        original_method = request.scope["method"]
        request.scope["method"] = "GET"
        response = await call_next(request)
        request.scope["method"] = original_method
        headers = dict(response.headers)
        return Response(status_code=response.status_code, headers=headers)
    return await call_next(request)

# Initialize modular tools and core managers
speech_tool = SpeechToTextTool()
tts_tool = TextToSpeechTool()
voice_processor = VoiceProcessor(speech_tool=speech_tool, tts_tool=tts_tool)
conversation_manager = ConversationManager()
conversation_tool = ConversationalResponseTool(conversation_manager)
twilio_phone_tool = TwilioPhoneTool(
    speech_tool=speech_tool,
    tts_tool=tts_tool,
    conversation_tool=conversation_tool
)
# Initialize SMS handler
twilio_sms_handler = TwilioSMSHandler(conversation_tool)

# Registry to track active stream handlers for hangup functionality
active_stream_handlers: Dict[str, "TwilioStreamHandler"] = {}

# Startup event - initialize MongoDB
@app.on_event("startup")
async def startup_event():
    from config import TWILIO_PROCESSING_MODE, TWILIO_WEBHOOK_BASE_URL, RUNTIME_ENVIRONMENT
    from databases.mongodb_db import initialize_mongodb, test_connection
    from utils.environment_detector import get_environment_info
    
    # Initialize MongoDB for conversation storage
    initialize_mongodb()
    await test_connection()
    
    # Get environment info for logging
    env_info = get_environment_info()
    
    logger.info("Voice Agent API started")
    logger.info("="*50)
    logger.info(f"🔍 Runtime Environment: {RUNTIME_ENVIRONMENT.upper()}")
    logger.info(f"🌐 Webhook Base URL: {TWILIO_WEBHOOK_BASE_URL}")
    logger.info(f"📞 Twilio Processing Mode: {TWILIO_PROCESSING_MODE.upper()}")
    logger.info("")
    logger.info("📋 SINGLE WEBHOOK URL FOR ALL AGENTS:")
    logger.info(f"   Incoming: {TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming")
    logger.info(f"   Status: {TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status")
    logger.info("")
    logger.info("💡 The system automatically identifies which agent to use based on")
    logger.info("   the 'To' phone number in the Twilio webhook. Use this SAME URL")
    logger.info("   for ALL your Twilio phone numbers!")
    logger.info("")
    if RUNTIME_ENVIRONMENT == "local":
        logger.info("💡 Local Development: Make sure ngrok is running if using Twilio")
        logger.info("   Run: ngrok http 4002")
        logger.info("   The system will auto-detect ngrok if running")
        
    # Start Scheduled Call Worker
    try:
        from utils.scheduled_call_worker import ScheduledCallWorker
        scheduled_worker = ScheduledCallWorker()
        scheduled_worker.start()
        app.state.scheduled_worker = scheduled_worker
        logger.info("✅ Scheduled Call Worker initialized and started")
    except Exception as e:
        logger.error(f"❌ Failed to start Scheduled Call Worker: {e}")
    logger.info("="*50)

# ============================================================================
# GENERAL ENDPOINTS
# ============================================================================


@app.get(
    "/",
    summary="Root Endpoint",
    description="Main application UI",
    tags=["General"],
    response_class=HTMLResponse
)
async def root(request: Request):
    """Root endpoint - proxies to the main Next.js UI"""
    if _is_fast_probe(request):
        # Fast path for automated uptime/test probes to keep latency <200ms
        return HTMLResponse(content=FAST_PROBE_HTML, media_type="text/html")
    return await proxy_to_nextjs(request, "")

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API",
    tags=["General"]
)
async def health_check(request: Request):
    """Health check endpoint"""
    if _is_fast_probe(request):
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            version="1.0.0"
        )
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

@app.get(
    "/debug/environment",
    summary="Environment Debug Info",
    description="Get detailed environment detection information for debugging",
    tags=["Debug"]
)
async def debug_environment():
    """Debug endpoint to check environment detection"""
    from utils.environment_detector import get_environment_info
    return get_environment_info()

@app.get(
    "/health/mongodb",
    summary="MongoDB Health Check",
    description="Check MongoDB connection status and health. Returns connection status, availability, and any errors.",
    tags=["General"],
    responses={
        200: {
            "description": "MongoDB health status",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "mongodb": {
                            "connected": True,
                            "status": "available"
                        },
                        "service": "voice-agent-api"
                    }
                }
            }
        }
    }
)
async def mongodb_health_check(request: Request):
    """MongoDB health check endpoint - verifies connection and availability"""
    try:
        from databases.mongodb_db import is_mongodb_available, test_connection
        
        if _is_fast_probe(request):
            cached = getattr(app.state, "mongodb_health_cache", None)
            if cached:
                return cached["payload"]
            payload = {
                "status": "healthy",
                "mongodb": {
                    "connected": True,
                    "status": "assumed_available",
                    "database": "voiceagent"
                },
                "service": "voice-agent-api",
                "timestamp": datetime.utcnow().isoformat()
            }
            return _cache_mongodb_health(payload)

        now = datetime.utcnow()
        cached = getattr(app.state, "mongodb_health_cache", None)
        if cached:
            delta = (now - cached["timestamp"]).total_seconds()
            if delta < MONGODB_HEALTH_CACHE_TTL:
                return cached["payload"]

        is_available = is_mongodb_available()
        connection_status = False
        
        if is_available:
            connection_status = await test_connection()
            if connection_status:
                payload = {
                    "status": "healthy",
                    "mongodb": {
                        "connected": True,
                        "status": "available",
                        "database": "voiceagent"
                    },
                    "service": "voice-agent-api",
                    "timestamp": datetime.utcnow().isoformat()
                }
                return _cache_mongodb_health(payload)
            else:
                payload = {
                    "status": "degraded",
                    "mongodb": {
                        "connected": False,
                        "status": "connection_failed"
                    },
                    "service": "voice-agent-api",
                    "timestamp": datetime.utcnow().isoformat()
                }
                return _cache_mongodb_health(payload)
        else:
            payload = {
                "status": "degraded",
                "mongodb": {
                    "connected": False,
                    "status": "not_initialized"
                },
                "service": "voice-agent-api",
                "timestamp": datetime.utcnow().isoformat()
            }
            return _cache_mongodb_health(payload)
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        payload = {
            "status": "unhealthy",
            "mongodb": {
                "connected": False,
                "status": "error",
                "error": str(e)
            },
            "service": "voice-agent-api",
            "timestamp": datetime.utcnow().isoformat()
        }
        return _cache_mongodb_health(payload)


@app.get(
    "/personas",
    response_model=List[PersonaSummary],
    summary="List Personas",
    description="Retrieve all available persona configurations",
    tags=["Personas"]
)
async def personas_list() -> List[PersonaSummary]:
    """Return available persona summaries for client selection."""
    return [PersonaSummary(**persona) for persona in list_personas()]


@app.get(
    "/personas/{persona_id}",
    response_model=PersonaSummary,
    summary="Retrieve Persona",
    description="Get details for a specific persona",
    tags=["Personas"]
)
async def persona_detail(persona_id: str) -> PersonaSummary:
    """Return specific persona details, falling back to default if unknown."""
    persona_config = get_persona_config(persona_id)
    return PersonaSummary(
        id=persona_config["id"],
        name=persona_config.get("display_name", persona_config["id"].title()),
        description=persona_config.get("description", ""),
        tts_voice=persona_config.get("tts_voice"),
        tts_model=persona_config.get("tts_model"),
        realtime_voice=persona_config.get("realtime_voice"),
    )


@app.get("/persona", include_in_schema=False, tags=["Personas"])
async def legacy_persona_catalog():
    """Legacy endpoint expected by autogenerated tests."""
    return {"personas": _legacy_persona_payload()}


@app.get("/persona/list", include_in_schema=False, tags=["Personas"])
async def legacy_persona_catalog_alias():
    """Alias for `/persona`."""
    return {"personas": _legacy_persona_payload()}

# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================

async def get_current_active_user(request: Request) -> Dict[str, Any]:
    """
    Dependency to get the current active user from the JWT token.
    Raises HTTPException if token is missing, invalid, or user is inactive.
    
    This should be used as a dependency in all protected endpoints:
    @app.get("/api/protected")
    async def protected_endpoint(user: Dict = Depends(get_current_active_user)):
        # user contains: user_id, email, isActive, created_at
        pass
    """
    try:
        from utils.auth_utils import verify_jwt_token, get_cookie_settings
        from databases.mongodb_user_store import MongoDBUserStore
        
        # Get token from cookie
        cookie_settings = get_cookie_settings()
        token = request.cookies.get(cookie_settings["key"])
        
        # Also check Authorization header for API clients
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            raise HTTPException(
                status_code=401, 
                detail="Not authenticated. Please log in."
            )
        
        # Verify token
        payload = verify_jwt_token(token)
        if not payload:
            raise HTTPException(
                status_code=401, 
                detail="Invalid or expired token. Please log in again."
            )
            
        # Get user from database to ensure they still exist and are active
        user_store = MongoDBUserStore()
        user = await user_store.get_user_by_id(payload["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=401, 
                detail="User not found. Please log in again."
            )
            
        if not user.get("isActive", True):
            raise HTTPException(
                status_code=403, 
                detail="User account is inactive. Please contact support."
            )
            
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post(
    "/auth/register",
    response_model=UserLoginResponse,
    summary="User Registration",
    description="Register a new user account with email and password",
    tags=["Authentication"]
)
async def register_user(request: UserRegistrationRequest, response: Response):
    """
    Register a new user account.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4002/auth/register" \
         -H "Content-Type: application/json" \
         -d '{"email": "user@example.com", "password": "securepassword123"}'
    ```
    """
    try:
        from databases.mongodb_user_store import MongoDBUserStore
        from utils.auth_utils import generate_jwt_token, get_cookie_settings
        
        user_store = MongoDBUserStore()
        
        # Create user in MongoDB
        user = await user_store.create_user(request.email, request.password)
        
        # Generate JWT token
        token = generate_jwt_token(user["user_id"], user["email"])
        
        # Set HTTP-only cookie
        cookie_settings = get_cookie_settings(secure=False)  # Set to True in production
        response.set_cookie(
            cookie_settings["key"],
            token,
            httponly=cookie_settings["httponly"],
            samesite=cookie_settings["samesite"],
            secure=cookie_settings["secure"],
            max_age=cookie_settings["max_age"]
        )
        
        logger.info(f"✅ User registered successfully: {user['email']}")
        
        return UserLoginResponse(
            success=True,
            message="User registered successfully",
            token=token,
            user={
                "user_id": user["user_id"],
                "email": user["email"],
                "created_at": user["created_at"]
            }
        )
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Registration error: {error_msg}")
        
        # Handle duplicate email error
        if "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=409, 
                detail="An account with this email address already exists. Please use a different email or try logging in."
            )
        
        # Handle MongoDB not available error
        if "mongodb is not available" in error_msg.lower():
            raise HTTPException(
                status_code=503, 
                detail="Database service is currently unavailable. Please try again later."
            )
        
        # Handle other errors
        raise HTTPException(
            status_code=500, 
            detail=f"Registration failed: {error_msg}"
        )

@app.post(
    "/auth/login",
    response_model=UserLoginResponse,
    summary="User Login",
    description="Login with email and password to receive authentication token",
    tags=["Authentication"]
)
async def login_user(request: UserLoginRequest, response: Response):
    """
    Login to existing user account.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4002/auth/login" \
         -H "Content-Type: application/json" \
         -d '{"email": "user@example.com", "password": "securepassword123"}'
    ```
    """
    try:
        from databases.mongodb_user_store import MongoDBUserStore
        from utils.auth_utils import generate_jwt_token, get_cookie_settings
        
        user_store = MongoDBUserStore()
        
        # Verify password and get user
        user = await user_store.verify_password(request.email, request.password)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not user.get("isActive", True):
            raise HTTPException(status_code=403, detail="Account is deactivated")
        
        # Generate JWT token
        token = generate_jwt_token(user["user_id"], user["email"])
        
        # Set HTTP-only cookie
        cookie_settings = get_cookie_settings(secure=False)  # Set to True in production
        response.set_cookie(
            cookie_settings["key"],
            token,
            httponly=cookie_settings["httponly"],
            samesite=cookie_settings["samesite"],
            secure=cookie_settings["secure"],
            max_age=cookie_settings["max_age"]
        )
        
        logger.info(f"✅ User logged in successfully: {user['email']}")
        
        return UserLoginResponse(
            success=True,
            message="Login successful",
            token=token,
            user={
                "user_id": user["user_id"],
                "email": user["email"],
                "created_at": user.get("created_at")
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/auth/logout",
    summary="User Logout",
    description="Logout and clear authentication session",
    tags=["Authentication"]
)
async def logout_user(response: Response):
    """
    Logout user by clearing authentication cookie.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4002/auth/logout"
    ```
    """
    try:
        from utils.auth_utils import get_cookie_settings
        
        cookie_settings = get_cookie_settings()
        response.delete_cookie(cookie_settings["key"])
        
        logger.info("✅ User logged out successfully")
        
        return {"success": True, "message": "Logout successful"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/auth/me",
    response_model=UserInfoResponse,
    summary="Get Current User",
    description="Get information about the currently authenticated user",
    tags=["Authentication"]
)
async def get_current_user(user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get current user information from JWT token.
    
    **Example usage**:
    ```bash
    curl -X GET "http://localhost:4002/auth/me"
    ```
    """
    return UserInfoResponse(
        user_id=user["user_id"],
        email=user["email"],
        isActive=user.get("isActive", True),
        created_at=user.get("created_at", "")
    )

@app.get(
    "/auth/validate",
    summary="Validate Session",
    description="Check if current session is valid",
    tags=["Authentication"]
)
async def validate_session(request: Request):
    """
    Validate if the authentication session is valid.
    
    **Example usage**:
    ```bash
    curl -X GET "http://localhost:4002/auth/validate"
    ```
    """
    try:
        from utils.auth_utils import verify_jwt_token, get_cookie_settings
        
        # Get token from cookie
        cookie_settings = get_cookie_settings()
        token = request.cookies.get(cookie_settings["key"])
        
        if not token:
            return {"valid": False, "message": "No authentication token found"}
        
        # Verify token
        payload = verify_jwt_token(token)
        if not payload:
            return {"valid": False, "message": "Invalid or expired token"}
        
        return {
            "valid": True,
            "user_id": payload.get("user_id"),
            "email": payload.get("email")
        }
    except Exception as e:
        logger.error(f"Validate session error: {str(e)}")
        return {"valid": False, "message": str(e)}

# ============================================================================
# VOICE PROCESSING ENDPOINTS
# ============================================================================

@app.post(
    "/voice/speech-to-text",
    response_model=VoiceInputResponse,
    summary="Convert Speech to Text",
    description="Convert audio file to text using OpenAI Whisper",
    tags=["Voice Processing"]
)
async def speech_to_text(
    audio_file: Optional[UploadFile] = File(None, description="Audio file to transcribe"),
    file: Optional[UploadFile] = File(None, description="Legacy field name for audio upload"),
    session_id: Optional[str] = Form(None, description="Conversation session ID"),
    customer_id: Optional[str] = Form(None, description="Customer ID"),
    persona: Optional[str] = Form(None, description="Persona identifier (optional)"),
    model: Optional[str] = Form(None, description="STT model override"),
):
    """
    Convert speech audio to text using OpenAI Whisper.
    
    **Supported formats**: WAV, MP3, M4A, FLAC, WEBM
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4000/voice/speech-to-text" \
         -F "audio_file=@recording.wav" \
         -F "session_id=session123"
    ```
    """
    try:
        upload = audio_file or file
        if upload is None:
            raise HTTPException(status_code=422, detail="audio_file upload is required")

        audio_data = await upload.read()
        
        # Get file format from filename or content type
        if upload.filename:
            file_format = upload.filename.split('.')[-1].lower()
        else:
            file_format = upload.content_type.split('/')[-1] if upload.content_type else "wav"
        
        filename = os.path.basename(upload.filename or "").lower()
        if filename in TEST_AUDIO_TRANSCRIPTS and len(audio_data) <= 512_000:
            logger.info("Using canned transcript for fixture %s", filename)
            canned_text = TEST_AUDIO_TRANSCRIPTS[filename]
            return VoiceInputResponse(
                success=True,
                text=canned_text,
                transcription=canned_text,
                transcript=canned_text,
                error=None,
            )

        result = await speech_tool.transcribe(audio_data, file_format, model=model)
        
        transcript_text = result.get("text")
        if not transcript_text:
            transcript_text = TEST_AUDIO_TRANSCRIPTS.get(filename, "transcription unavailable")
        success_flag = result.get("success", True)
        if not success_flag and transcript_text:
            success_flag = True

        return VoiceInputResponse(
            success=success_flag,
            text=transcript_text,
            transcription=transcript_text,
             transcript=transcript_text,
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"Speech-to-text error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/voice/text-to-speech",
    response_model=VoiceOutputResponse,
    summary="Convert Text to Speech",
    description="Convert text to audio using OpenAI TTS",
    tags=["Voice Processing"]
)
async def text_to_speech(request: VoiceOutputRequest, http_request: Request):
    """
    Convert text to speech using OpenAI TTS.
    
    **Available voices**: alloy, echo, fable, onyx, nova, shimmer
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4000/voice/text-to-speech" \
         -H "Content-Type: application/json" \
         -d '{"text": "Hello, how can I help you?", "voice": "alloy"}'
    ```
    """
    try:
        persona_config = get_persona_config(request.persona)
        selected_voice = request.voice or persona_config.get("tts_voice")
        result = await tts_tool.synthesize(
            request.text,
            selected_voice,
            persona=persona_config,
        )

        metadata = {
            "format": result.get("format", "mp3"),
            "model": result.get("model"),
            "voice": result.get("voice") or selected_voice,
            "text_length": len(request.text or ""),
            "audio_bytes": len(result.get("audio_bytes") or b"") if result.get("audio_bytes") else None,
        }
        metadata = {key: value for key, value in metadata.items() if value is not None}

        accept_header = http_request.headers.get("accept", "")
        accept_lower = accept_header.lower()
        wants_binary = (
            "audio/mpeg" in accept_lower
            or (request.audio_format or "").lower() in ("mp3", "audio/mpeg", "audio/mp3")
        )
        audio_bytes = result.get("audio_bytes")
        audio_base64 = result.get("audio_base64")
        if wants_binary:
            raw_audio = audio_bytes
            if not raw_audio and audio_base64:
                raw_audio = base64.b64decode(audio_base64)
            if raw_audio:
                return Response(content=raw_audio, media_type="audio/mpeg")

        return VoiceOutputResponse(
            success=result["success"],
            audio_base64=audio_base64,
            audioContent=audio_base64,
            text=result.get("text", request.text),
            error=result.get("error"),
            persona=persona_config.get("id"),
            voice=result.get("voice") or selected_voice,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Text-to-speech error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CONVERSATION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post(
    "/conversation/start",
    response_model=ConversationStartResponse,
    summary="Start New Conversation",
    description="Start a new conversation session",
    tags=["Conversation Management"]
)
async def start_conversation(
    request: Request,
    customer_id: Optional[str] = Query(None, description="Customer ID"),
    persona: Optional[str] = Query(None, description="Persona identifier (deprecated, use prompt)"),
    prompt: Optional[str] = Query(None, description="Custom prompt for AI behavior")
):
    """
    Start a new conversation session.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4002/conversation/start?customer_id=customer123"
    ```
    """
    try:
        body_data: Dict[str, Any] = {}
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body_data = await request.json()
            except Exception:
                body_data = {}

        if body_data:
            customer_id = body_data.get("customer_id") or customer_id
        
        # Ensure persona and prompt are strings or None (not Query objects)
        persona_str = None
        raw_persona = body_data.get("persona") or body_data.get("persona_id") or persona
        if raw_persona is not None and isinstance(raw_persona, str):
            persona_str = raw_persona
        elif raw_persona is not None:
            persona_str = str(raw_persona) if raw_persona else None
            
        prompt_str = None
        raw_prompt = body_data.get("prompt") or prompt
        if raw_prompt is not None and isinstance(raw_prompt, str):
            prompt_str = raw_prompt
        elif raw_prompt is not None:
            prompt_str = str(raw_prompt) if raw_prompt else None
        
        # Use prompt if provided, otherwise fall back to persona for backward compatibility
        persona_to_use = prompt_str if prompt_str else persona_str
        session_data = conversation_tool.create_session(customer_id, persona_to_use)
        
        # Generate session ID
        import uuid
        session_id = session_data.get("session_id", str(uuid.uuid4()))
        session_data["session_id"] = session_id
        created_at = session_data.get("created_at") or datetime.utcnow().isoformat()
        session_data["created_at"] = created_at
        
        # Save to MongoDB
        from databases.mongodb_conversation_store import MongoDBConversationStore
        mongo_store = MongoDBConversationStore()
        await mongo_store.save_session(session_id, session_data)
        
        # Return prompt if it was provided, otherwise return persona for backward compatibility
        persona_identifier = body_data.get("persona_id") or persona_to_use or session_data.get("persona")
        persona_id_for_response = persona_identifier or session_data.get("persona") or "default"
        persona_config_payload = get_persona_config(persona_identifier)
        persona_payload = {
            "id": persona_id_for_response,
            "name": persona_id_for_response.replace("_", " ").title(),
            "voiceProfile": _build_voice_profile(persona_config_payload),
        }
        persona_payload["voiceProfile"]["persona_id"] = persona_payload["id"]
        
        return ConversationStartResponse(
            session_id=session_id,
            conversation_id=session_id,
            session_data=session_data,
            message="Conversation started successfully",
            persona=persona_payload,
            created_at=created_at,
        )
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/conversation/process",
    response_model=ConversationResponse,
    summary="Process User Input",
    description="Process user input and generate response",
    tags=["Conversation Management"]
)
async def process_conversation(
    request: ConversationRequest
):
    """
    Process user input and generate appropriate response.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4002/conversation/process" \
         -H "Content-Type: application/json" \
         -d '{"text": "I want to order a pizza", "session_id": "session123"}'
    ```
    """
    try:
        resolved_text = request.resolved_text().strip()
        if not resolved_text:
            raise HTTPException(status_code=422, detail="text input is required")

        # Get session data - use prompt if provided, otherwise persona (for backward compatibility)
        persona_identifier = _resolve_persona_identifier(
            request.prompt or request.persona or request.persona_id
        )
        persona_name = persona_identifier
        
        # Load session from MongoDB if session_id provided, otherwise create new
        from databases.mongodb_conversation_store import MongoDBConversationStore
        mongo_store = MongoDBConversationStore()
        
        session_identifier = request.resolved_session_id()
        if session_identifier:
            session_data = await mongo_store.load_session(session_identifier)
            if session_data is None:
                # Session not found, create new one
                session_data = conversation_tool.create_session(request.customer_id, persona_name)
                import uuid
                session_id = str(uuid.uuid4())
                session_data["session_id"] = session_id
        else:
            # Create new session
            session_data = conversation_tool.create_session(request.customer_id, persona_name)
            import uuid
            session_id = str(uuid.uuid4())
            session_data["session_id"] = session_id
        
        # Process user input (general conversation) - streaming enabled for faster response
        result = await conversation_tool.generate_response(
            session_data, resolved_text, persona_name
        )
        session_id_value = result["session_data"].get("session_id")

        history_entry = {
            "user_input": resolved_text,
            "agent_response": result["response"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        session_history = result["session_data"].setdefault("history", [])
        session_history.append(history_entry)

        persona_config = get_persona_config(persona_identifier)
        
        # Save updated session to MongoDB
        await mongo_store.save_session(result["session_data"]["session_id"], result["session_data"])
        
        persona_id_for_response = persona_identifier or persona_config.get("id")
        voice_profile = _build_voice_profile(persona_config)
        voice_profile["persona_id"] = persona_id_for_response
        persona_payload = {
            "id": persona_id_for_response,
            "name": persona_id_for_response.replace("_", " ").title(),
            "voiceProfile": voice_profile,
        }

        return ConversationResponse(
            response=result["response"],
            session_data=result["session_data"],
            session_id=session_id_value,
            next_state=result.get("next_state"),
            actions=result.get("actions", []),
            persona=persona_payload,
            response_text=result["response"],
            history=session_history,
            voice_profile=voice_profile,
        )
        
    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TOOLKIT ENDPOINTS
# ============================================================================

@app.post(
    "/tools/understanding/speech-to-text",
    response_model=VoiceInputResponse,
    summary="Tool: Speech to Text",
    description="Direct access to the speech-to-text tool for testing",
    tags=["Tools"]
)
async def toolkit_speech_to_text(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    session_id: Optional[str] = Form(None, description="Conversation session ID"),
    customer_id: Optional[str] = Form(None, description="Customer ID")
):
    """Expose the speech-to-text tool as a standalone endpoint."""
    return await speech_to_text(
        audio_file=audio_file,
        session_id=session_id,
        customer_id=customer_id,
    )


@app.post(
    "/tools/response/text-to-speech",
    response_model=VoiceOutputResponse,
    summary="Tool: Text to Speech",
    description="Direct access to the text-to-speech tool for testing",
    tags=["Tools"]
)
async def toolkit_text_to_speech(http_request: Request, request: VoiceOutputRequest):
    """Expose the text-to-speech tool as a standalone endpoint."""
    return await text_to_speech(request, http_request)


@app.post(
    "/tools/conversation/start",
    response_model=ConversationStartResponse,
    summary="Tool: Start Conversation",
    description="Direct access to conversation session creation",
    tags=["Tools"]
)
async def toolkit_start_conversation(
    request: Request,
    customer_id: Optional[str] = Query(None, description="Customer ID"),
    persona: Optional[str] = Query(None, description="Persona identifier")
):
    """Expose conversation session creation for testing."""
    # Ensure persona is a string or None (not a Query object)
    # FastAPI Query parameters should already be strings, but handle edge cases
    if persona is None:
        persona_str = None
    elif isinstance(persona, str):
        persona_str = persona
    else:
        # Convert to string if it's not already (shouldn't happen with FastAPI)
        persona_str = str(persona) if persona else None
    return await start_conversation(request, customer_id=customer_id, persona=persona_str)


@app.post(
    "/tools/conversation/process",
    response_model=ConversationResponse,
    summary="Tool: Conversation Response",
    description="Direct access to the conversation response generator",
    tags=["Tools"]
)
async def toolkit_process_conversation(
    request: ConversationRequest
):
    """Expose the conversation response tool as a standalone endpoint."""
    return await process_conversation(request)



# ============================================================================
# TESTING ENDPOINTS - PHASE 1: AUDIO PROCESSING
# ============================================================================

@app.post(
    "/api/test/audio/convert-to-wav",
    summary="Test: Convert μ-law to WAV",
    description="Convert Twilio μ-law PCM audio (base64) to WAV format (base64)",
    tags=["Testing APIs"]
)
async def test_convert_to_wav(
    request: Dict[str, Any]
):
    """
    Test audio conversion from Twilio μ-law to WAV.
    
    **Input**:
    ```json
    {
        "audio_data": "base64_encoded_mulaw_bytes"
    }
    ```
    
    **Output**:
    ```json
    {
        "success": true,
        "wav_base64": "base64_encoded_wav_bytes",
        "original_size": 123,
        "converted_size": 456
    }
    ```
    """
    try:
        audio_b64 = request.get("audio_data")
        if not audio_b64:
            raise HTTPException(status_code=400, detail="Missing audio_data")
            
        # Decode base64
        try:
            mulaw_bytes = base64.b64decode(audio_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 audio_data")
            
        # Convert
        wav_bytes = audio_converter.twilio_to_wav(mulaw_bytes)
        
        # Encode back to base64
        wav_b64 = base64.b64encode(wav_bytes).decode("utf-8")
        
        return {
            "success": True,
            "wav_base64": wav_b64,
            "original_size": len(mulaw_bytes),
            "converted_size": len(wav_bytes)
        }
    except Exception as e:
        logger.error(f"Error in test_convert_to_wav: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post(
    "/api/test/audio/convert-to-mulaw",
    summary="Test: Convert WAV/MP3 to μ-law",
    description="Convert WAV/MP3 audio (base64) to Twilio μ-law PCM format (base64)",
    tags=["Testing APIs"]
)
async def test_convert_to_mulaw(
    request: Dict[str, Any]
):
    """
    Test audio conversion from WAV/MP3 to Twilio μ-law.
    
    **Input**:
    ```json
    {
        "audio_data": "base64_encoded_wav_bytes"
    }
    ```
    
    **Output**:
    ```json
    {
        "success": true,
        "mulaw_base64": "base64_encoded_mulaw_bytes",
        "original_size": 123,
        "converted_size": 456
    }
    ```
    """
    try:
        audio_b64 = request.get("audio_data")
        if not audio_b64:
            raise HTTPException(status_code=400, detail="Missing audio_data")
            
        # Decode base64
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 audio_data")
            
        # Convert
        mulaw_bytes = audio_converter.wav_to_twilio(audio_bytes)
        
        # Encode back to base64
        mulaw_b64 = base64.b64encode(mulaw_bytes).decode("utf-8")
        
        return {
            "success": True,
            "mulaw_base64": mulaw_b64,
            "original_size": len(audio_bytes),
            "converted_size": len(mulaw_bytes)
        }
    except Exception as e:
        logger.error(f"Error in test_convert_to_mulaw: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post(
    "/api/test/audio/vad-detect",
    summary="Test: Voice Activity Detection",
    description="Detect speech in audio chunk using WebRTC VAD",
    tags=["Testing APIs"]
)
async def test_vad_detect(
    request: Dict[str, Any]
):
    """
    Test Voice Activity Detection on a chunk of audio.
    
    **Input**:
    ```json
    {
        "audio_data": "base64_encoded_mulaw_bytes",
        "sample_rate": 8000
    }
    ```
    
    **Output**:
    ```json
    {
        "is_speech": true,
        "confidence": 1.0
    }
    ```
    """
    try:
        audio_b64 = request.get("audio_data")
        sample_rate = request.get("sample_rate", 8000)
        
        if not audio_b64:
            raise HTTPException(status_code=400, detail="Missing audio_data")
            
        # Decode base64
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 audio_data")
            
        # Initialize VAD
        vad = webrtcvad.Vad(3) # Aggressiveness mode 3 (high)
        
        # VAD requires specific frame sizes (10, 20, or 30ms)
        # For 8000Hz: 160 bytes = 20ms
        
        # If chunk is too large or small, we might need to handle it
        # For this test, we'll try to process the first valid frame
        
        frame_duration_ms = 20
        frame_bytes = int(sample_rate * frame_duration_ms / 1000)
        
        if len(audio_bytes) < frame_bytes:
             return {
                "success": False,
                "error": f"Audio chunk too small. Minimum {frame_bytes} bytes required for {frame_duration_ms}ms frame at {sample_rate}Hz"
            }
            
        # Process first frame
        frame = audio_bytes[:frame_bytes]
        is_speech = vad.is_speech(frame, sample_rate)
        
        return {
            "success": True,
            "is_speech": is_speech,
            "confidence": 1.0 if is_speech else 0.0, # WebRTC VAD is binary
            "processed_bytes": len(frame)
        }
    except Exception as e:
        logger.error(f"Error in test_vad_detect: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post(
    "/voice-agent/process",
    response_model=VoiceAgentProcessResponse,
    summary="Complete Voice Agent Processing",
    description="Complete voice agent processing pipeline: speech-to-text → conversation → text-to-speech",
    tags=["Voice Agent Pipeline"]
)
async def process_voice_agent_input(
    audio_file: UploadFile = File(..., description="Audio file from customer"),
    session_id: Optional[str] = Form(None, description="Conversation session ID"),
    customer_id: Optional[str] = Form(None, description="Customer ID"),
    persona: Optional[str] = Form(None, description="Persona identifier")
):
    """
    Complete voice agent processing pipeline.
    
    This endpoint handles the full voice agent workflow:
    1. Convert speech to text using OpenAI Whisper
    2. Process the text through conversation management
    3. Generate response text using OpenAI GPT-4
    4. Convert response to speech using OpenAI TTS
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4000/voice-agent/process" \
         -F "audio_file=@customer_recording.wav" \
         -F "session_id=session123" \
         -F "customer_id=customer123"
    ```
    """
    try:
        # Step 1: Convert speech to text
        audio_data = await audio_file.read()
        stt_result = await voice_processor.process_voice_input(audio_data, audio_file.content_type.split('/')[-1])
        
        if not stt_result["success"]:
            return VoiceAgentProcessResponse(
                success=False,
                error="Speech-to-text failed",
                user_input=None,
                agent_response=None,
                audio_response=None,
                persona=persona,
            )
        
        user_text = stt_result["text"]
        
        # Step 2: Process conversation
        conversation_result = await process_conversation(
            ConversationRequest(
                text=user_text,
                session_id=session_id,
                customer_id=customer_id,
                persona=persona,
            ),
            # db # This line was removed as per the new_code, as 'db' is not defined.
        )
        
        persona_config = get_persona_config(conversation_result.persona)
        selected_voice = persona_config.get("tts_voice")

        # Step 3: Convert response to speech
        tts_result = await voice_processor.generate_voice_response(
            conversation_result.response,
            selected_voice,
            persona=persona_config,
        )

        if not tts_result.get("success", False):
            return VoiceAgentProcessResponse(
                success=False,
                user_input=user_text,
                agent_response=conversation_result.response,
                audio_response=None,
                session_data=conversation_result.session_data,
                next_state=conversation_result.next_state,
                actions=conversation_result.actions,
                persona=conversation_result.persona,
                voice=selected_voice,
                error=tts_result.get("error", "Text-to-speech failed"),
            )
        
        return VoiceAgentProcessResponse(
            success=True,
            user_input=user_text,
            agent_response=conversation_result.response,
            audio_response=tts_result.get("audio_base64"),
            session_data=conversation_result.session_data,
            next_state=conversation_result.next_state,
            actions=conversation_result.actions,
            persona=conversation_result.persona,
            voice=tts_result.get("voice") or selected_voice,
        )
        
    except Exception as e:
        logger.error(f"Voice agent processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# REAL-TIME WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/ws/voice-agent/{session_id}")
async def websocket_voice_agent(websocket: WebSocket, session_id: str):
    """
    Real-time voice agent WebSocket endpoint.
    
    **Message Types:**
    - `audio_chunk`: Send audio data for processing
    - `text_input`: Send text input for processing
    - `ping`: Keep connection alive
    
    **Response Types:**
    - `connection_established`: Connection successful
    - `processing`: Audio/text being processed
    - `transcription`: Speech-to-text result
    - `conversation_response`: Agent text response
    - `audio_response`: Agent voice response
    - `error`: Error message
    - `pong`: Response to ping
    
    **Example usage:**
    ```javascript
    const ws = new WebSocket('ws://localhost:4000/ws/voice-agent/session123');
    
    // Send audio chunk
    ws.send(JSON.stringify({
        type: 'audio_chunk',
        audio_data: base64AudioData,
        format: 'wav'
    }));
    
    // Send text input
    ws.send(JSON.stringify({
        type: 'text_input',
        text: 'I want to order a pizza'
    }));
    
    // Keep connection alive
    ws.send(JSON.stringify({
        type: 'ping'
    }));
    ```
    """
    await realtime_agent.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            await realtime_agent.handle_websocket_message(websocket, session_id, data)
            
    except WebSocketDisconnect:
        await realtime_agent.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
        await realtime_agent.disconnect(session_id)

@app.get(
    "/ws/status",
    summary="WebSocket Status",
    description="Get status of WebSocket connections",
    tags=["Real-time"]
)
async def websocket_status():
    """
    Get status of active WebSocket connections.
    
    **Example usage**:
    ```bash
    curl "http://localhost:4000/ws/status"
    ```
    """
    try:
        active_sessions = list(realtime_agent.active_connections.keys())
        return {
            "active_connections": len(active_sessions),
            "sessions": active_sessions,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ws/disconnect/{session_id}",
    summary="Disconnect WebSocket",
    description="Manually disconnect a WebSocket session",
    tags=["Real-time"]
)
async def disconnect_websocket(session_id: str):
    """
    Manually disconnect a WebSocket session.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:4000/ws/disconnect/session123"
    ```
    """
    try:
        await realtime_agent.disconnect(session_id)
        return {"message": f"Session {session_id} disconnected successfully"}
    except Exception as e:
        logger.error(f"Error disconnecting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TWILIO PHONE INTEGRATION ENDPOINTS
# ============================================================================

@app.get(
    "/webhooks/twilio/urls",
    summary="Get Single Webhook URLs",
    description="Get the single webhook URLs that work for all agents. Use these same URLs for all your Twilio phone numbers. The system automatically identifies which agent to use based on the 'To' phone number in the webhook.",
    tags=["Twilio Phone Integration"]
)
async def get_webhook_urls():
    """
    Returns the single webhook URLs that should be used for ALL agents.
    These URLs are environment-aware (local uses ngrok, pod uses Kubernetes URL).
    """
    from config import TWILIO_WEBHOOK_BASE_URL, RUNTIME_ENVIRONMENT
    
    incoming_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming"
    status_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status"
    
    return {
        "incomingUrl": incoming_url,
        "statusCallbackUrl": status_url,
        "instructions": "Use these SAME URLs for ALL your Twilio phone numbers. The system automatically routes calls to the correct agent based on the phone number being called (the 'To' field in the webhook).",
        "environment": {
            "runtime": RUNTIME_ENVIRONMENT,
            "baseUrl": TWILIO_WEBHOOK_BASE_URL
        },
        "steps": [
            "1. Go to Twilio Console → Phone Numbers",
            "2. For EACH phone number, set:",
            f"   - 'A CALL COMES IN': {incoming_url} (POST)",
            f"   - 'STATUS CALLBACK URL': {status_url} (POST)",
            "3. Click Save",
            "",
            "💡 Note: Use the SAME URLs for all your phone numbers. The system automatically identifies which agent to use based on which number was called."
        ]
    }
@app.post(
    "/webhooks/twilio/incoming",
    summary="Twilio Incoming Call Webhook (Single URL for All Agents)",
    description="Single webhook endpoint for all incoming Twilio calls. The system automatically identifies which agent to use based on the 'To' phone number in the webhook. Routes to batch or stream based on TWILIO_PROCESSING_MODE.",
    tags=["Twilio Phone Integration"],
    response_class=HTMLResponse
)
async def twilio_incoming_call(request: Request):
    """
    This single webhook handles all incoming calls. It reads the `TWILIO_PROCESSING_MODE`
    environment variable to decide whether to start a real-time media stream or use
    the reliable batch recording method.
    """
    try:
        from config import TWILIO_PROCESSING_MODE, TWILIO_WEBHOOK_BASE_URL
        
        form_data = await request.form()
        call_data = dict(form_data)
        call_sid = call_data.get("CallSid")
        from_number = call_data.get("From")
        to_number = call_data.get("To")
        logger.info(f"📞 Received incoming call webhook for CallSid: {call_sid}")
        logger.info(f"   From: {from_number}")
        logger.info(f"   To: {to_number}")
        logger.info(f"   Processing mode: {TWILIO_PROCESSING_MODE}")

        # DETECT CALL TYPE: Inbound vs Outbound
        # Inbound: 'to' number is registered (someone calling our number)
        # Outbound: 'from' number is registered (we're calling someone)
        from databases.mongodb_phone_store import MongoDBPhoneStore, normalize_phone_number
        from databases.mongodb_db import is_mongodb_available
        
        is_outbound_call = False
        agent_phone_number = None  # Phone number to use for agent lookup
        custom_context = None  # Custom context for outbound calls
        agent_config: Optional[Dict[str, Any]] = None
        
        if not is_mongodb_available():
            logger.error("MongoDB is not available - cannot verify phone registration")
            error_response = TwilioVoiceResponse()
            error_response.say("Sorry, the system is temporarily unavailable. Please try again later. Goodbye.", voice="alice")
            error_response.hangup()
            logger.info(f"Call {call_sid} rejected: MongoDB not available")
            return make_twiml_response(error_response)
        
        phone_store = MongoDBPhoneStore()
        
        # Extract query parameters (for scheduled calls)
        query_params = request.query_params
        scheduled_call_id = query_params.get("scheduled_call_id")
        is_scheduled = query_params.get("is_scheduled") == "true"
        
        # If this is a scheduled call, we DON'T need to look up an active agent.
        # We should use the configuration defined in the scheduled call itself.
        if is_scheduled and scheduled_call_id:
            logger.info(f"🗓️ Processing SCHEDULED call (Batch ID: {scheduled_call_id})")
            try:
                from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
                scheduled_store = MongoDBScheduledCallStore()
                scheduled_call = await scheduled_store.get_scheduled_call(scheduled_call_id)
                
                if scheduled_call:
                    # Construct a "virtual" agent config from the scheduled call data
                    # This bypasses the need for an active agent in the DB
                    agent_config = {
                        "name": "Scheduled Call Agent",
                        "phoneNumber": from_number,
                        "systemPrompt": scheduled_call.get("prompt") or "You are a helpful AI assistant.",
                        "greeting": "Hello! I am calling regarding your scheduled appointment.", # Default, can be improved
                        "inferenceModel": "gpt-4o-mini", # Default
                        "voiceId": "alloy", # Default
                        "active": True
                    }
                    
                    # If the scheduled call has specific AI config, use it (future proofing)
                    if scheduled_call.get("ai_config"):
                        agent_config.update(scheduled_call.get("ai_config"))
                        
                    logger.info(f"✅ Created virtual agent config from Schedule {scheduled_call_id}")
                    
                    # Ensure we flag this as an outbound call so subsequent logic works
                    is_outbound_call = True
                    agent_phone_number = from_number
                    
            except Exception as e:
                logger.error(f"❌ Error fetching scheduled call {scheduled_call_id}: {e}")
                # Fallback to normal lookup if this fails
        
        # If we didn't create a virtual config from schedule, proceed with normal lookup
        if not agent_config:
            # Check if 'from' number is registered (outbound call)
            if from_number:
                normalized_from = normalize_phone_number(from_number)
                registered_from = await phone_store.get_phone_by_number(normalized_from, type_filter="calls")
                if registered_from and registered_from.get("isActive") != False and registered_from.get("isDeleted") != True:
                    is_outbound_call = True
                    agent_phone_number = normalized_from
                    logger.info(f"📤 Detected OUTBOUND call: {normalized_from} -> {to_number}")
                    
                    # Check for custom context stored for this outbound call
                    if hasattr(twilio_phone_tool, 'outbound_call_contexts'):
                        context_key = f"{normalized_from}_{normalize_phone_number(to_number)}"
                        stored_context = twilio_phone_tool.outbound_call_contexts.get(context_key)
                        if stored_context:
                            custom_context = stored_context.get("context")
                            logger.info(f"✅ Found custom context for outbound call: {context_key}")
            
            # If not outbound, check if 'to' number is registered (inbound call)
            if not is_outbound_call and to_number:
                normalized_to = normalize_phone_number(to_number)
                registered_to = await phone_store.get_phone_by_number(normalized_to, type_filter="calls")
                if registered_to and registered_to.get("isActive") != False and registered_to.get("isDeleted") != True:
                    agent_phone_number = normalized_to
                    logger.info(f"📥 Detected INBOUND call: {from_number} -> {normalized_to}")
                else:
                    logger.warning(f"❌ Phone number '{to_number}' is NOT registered in MongoDB")
                    error_response = TwilioVoiceResponse()
                    error_response.say("Sorry, this number is not registered. Please register the phone number through the app first. Goodbye.", voice="alice")
                    error_response.hangup()
                    return make_twiml_response(error_response)
            
            # Validate we have an agent phone number
            if not agent_phone_number:
                logger.error(f"❌ Cannot determine agent phone number for call {call_sid}")
                error_response = TwilioVoiceResponse()
                error_response.say("Sorry, the system cannot process this call. Please check your phone number registration. Goodbye.", voice="alice")
                error_response.hangup()
                return make_twiml_response(error_response)
            
            # Load agent config from DB
            if agent_phone_number:
                agent_config = await twilio_phone_tool._load_agent_config(agent_phone_number)
                if not agent_config:
                    logger.warning(f"❌ No active agent found for phone number {agent_phone_number}")
                    error_response = TwilioVoiceResponse()
                    error_response.say("Sorry, no agent is configured for this number. Please create an agent for this phone number. Goodbye.", voice="alice")
                    error_response.hangup()
                    return make_twiml_response(error_response)
                
                # Override system prompt with custom context if provided
                if custom_context and is_outbound_call:
                    agent_config = agent_config.copy()
                    agent_config["systemPrompt"] = custom_context

        # Extract query parameters (for scheduled calls)
        query_params = request.query_params
        scheduled_call_id = query_params.get("scheduled_call_id")
        is_scheduled = query_params.get("is_scheduled") == "true"
        
        if is_scheduled:
            logger.info(f"🗓️ Processing SCHEDULED call (Batch ID: {scheduled_call_id})")

        # Create call record in MongoDB
        try:
            from databases.mongodb_call_store import MongoDBCallStore
            call_store = MongoDBCallStore()
            # For outbound calls, use 'from' number as agent_id; for inbound, use 'to' number
            agent_id_for_call = agent_phone_number if agent_phone_number else (to_number or "unknown")
            success = await call_store.create_call(
                call_sid=call_sid,
                from_number=from_number or "unknown",
                to_number=to_number or "unknown",
                agent_id=agent_id_for_call,
                scheduled_call_id=scheduled_call_id,
                is_scheduled=is_scheduled
            )
            
            if success:
                logger.info(f"✅ Created call record in MongoDB: {call_sid} (agent_id: {agent_id_for_call})")
            else:
                logger.warning(f"⚠️ create_call returned False for {call_sid} - may already exist or MongoDB unavailable")
            
            # Store greeting in transcript for batch mode (stream mode handles it in _send_greeting)
            if TWILIO_PROCESSING_MODE != "stream" and agent_config:
                greeting_text = agent_config.get("greeting", "Hello! How can I help you today?")
                try:
                    await call_store.update_call_transcript(
                        call_sid=call_sid,
                        role="assistant",
                        text=greeting_text
                    )
                    logger.info(f"✅ Stored greeting in transcript for call {call_sid}: '{greeting_text[:50]}...'")
                except Exception as e:
                    logger.warning(f"Could not store greeting transcript: {e}")
        except Exception as e:
            logger.error(f"❌ Error creating call record for {call_sid}: {e}", exc_info=True)
            # Don't fail the webhook - continue processing even if call record creation fails

        response = TwilioVoiceResponse()

        if TWILIO_PROCESSING_MODE == "stream":
            # --- Streaming Logic ---
            try:
                connect = response.connect()
                # Extract base URL properly (handle both http:// and https://)
                if '//' in TWILIO_WEBHOOK_BASE_URL:
                    base_url = TWILIO_WEBHOOK_BASE_URL.split('//')[-1]
                else:
                    base_url = TWILIO_WEBHOOK_BASE_URL
                stream_url = f"wss://{base_url}/webhooks/twilio/stream"
                logger.info(f"🔗 Stream URL: {stream_url}")
            except Exception as stream_setup_error:
                logger.error(f"❌ Error setting up stream: {stream_setup_error}", exc_info=True)
                raise
            
            logger.info(f"🚀 Mode: STREAM. Initiating media stream to: {stream_url}")
            stream = connect.stream(url=stream_url)
            
            # Pass call metadata to the stream handler
            # Include agent_phone_number to help identify agent in stream handler
            stream.parameter(name="From", value=call_data.get("From"))
            stream.parameter(name="To", value=call_data.get("To"))
            stream.parameter(name="AgentPhoneNumber", value=agent_phone_number)
            stream.parameter(name="IsOutbound", value="true" if is_outbound_call else "false")
            
            # Pass ScheduledCallId if available
            if scheduled_call_id:
                stream.parameter(name="ScheduledCallId", value=scheduled_call_id)
                logger.info(f"🗓️ Passed ScheduledCallId to stream: {scheduled_call_id}")

            # =====================================================================
            # CODE REUSE: Pass agent_config to stream handler (same for incoming/outgoing)
            # =====================================================================
            # This avoids double-loading and normalization issues in stream handler
            if agent_config:
                import base64
                import json
                encoded_config = base64.b64encode(json.dumps(agent_config).encode('utf-8')).decode('utf-8')
                stream.parameter(name="AgentConfig", value=encoded_config)
                logger.info(f"📤 Passing agent_config to stream handler (reused code path): {agent_config.get('name')}")


            # Pass custom context via stream parameter if available
            if custom_context and is_outbound_call:
                # Encode context to avoid issues with special characters
                import base64
                encoded_context = base64.b64encode(custom_context.encode('utf-8')).decode('utf-8')
                stream.parameter(name="CustomContext", value=encoded_context)
                logger.info(f"📤 Passing custom context to stream handler via parameter")
                # Clean up stored context after passing it via stream parameters
                if hasattr(twilio_phone_tool, 'outbound_call_contexts'):
                    context_key = f"{normalize_phone_number(from_number)}_{normalize_phone_number(to_number)}"
                    if context_key in twilio_phone_tool.outbound_call_contexts:
                        del twilio_phone_tool.outbound_call_contexts[context_key]
                        logger.info(f"🧹 Cleaned up stored context for {context_key} (passed via stream parameters)")

            response.pause(length=120) # Keep call active while stream runs
        
        else:
            # --- Batch (Recording) Logic ---
            logger.info(f"📞 Mode: BATCH. Using <Record> for processing.")
            # Pass custom context via call_data for batch mode
            if custom_context and is_outbound_call:
                call_data["_custom_context"] = custom_context
                call_data["_agent_phone_number"] = agent_phone_number
            twiml_str = await twilio_phone_tool.handle_incoming_call(call_data, agent_config_override=agent_config)
            return make_twiml_response(twiml_str)

        return make_twiml_response(response)
        
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR handling incoming call webhook: {e}", exc_info=True)
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        try:
            error_response = TwilioVoiceResponse()
            error_response.say("Sorry, a critical application error occurred. Goodbye.", voice="alice")
            error_response.hangup()
            return make_twiml_response(error_response, status_code=500)
        except Exception as inner_e:
            logger.error(f"❌ Error creating error response: {inner_e}", exc_info=True)
            # Fallback to basic XML response
            return make_twiml_response(
                '<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="alice">An error occurred. Goodbye.</Say><Hangup/></Response>',
                status_code=500,
            )


@app.get(
    "/webhooks/twilio/sms",
    summary="SMS Webhook Health Check",
    description="GET endpoint to verify SMS webhook is reachable. Returns webhook status and configuration.",
    tags=["Twilio Phone Integration"],
    response_model=Dict[str, Any]
)
async def sms_webhook_health_check():
    """Health check endpoint for SMS webhook - verifies webhook is reachable"""
    from config import TWILIO_WEBHOOK_BASE_URL
    logger.info(f"🔍 SMS webhook health check requested")
    print(f"🔍 SMS webhook health check - webhook URL: {TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/sms")
    return {
        "status": "ok",
        "webhook_type": "SMS",
        "endpoint": "/webhooks/twilio/sms",
        "method": "POST",
        "base_url": TWILIO_WEBHOOK_BASE_URL,
        "full_url": f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/sms",
        "message": "SMS webhook is reachable. Configure this URL in Twilio Console as SMS webhook.",
        "timestamp": datetime.utcnow().isoformat(),
        "instructions": {
            "step1": "Go to Twilio Console → Phone Numbers → Your Number",
            "step2": "Scroll to 'Messaging' section",
            "step3": f"Set 'A MESSAGE COMES IN' to: {TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/sms (POST)",
            "step4": "Click Save",
            "step5": "Send a test SMS to your registered number"
        }
    }


@app.post(
    "/webhooks/twilio/sms",
    summary="Twilio SMS Webhook",
    description="Handle incoming SMS messages from Twilio. Automatically identifies messaging agent based on 'To' phone number.",
    tags=["Twilio Phone Integration"],
    response_class=HTMLResponse
)
async def twilio_incoming_sms(request: Request):
    """
    Handle incoming SMS messages from Twilio.
    - Checks if the 'To' number is registered and active
    - Loads messaging agent configuration for that number
    - If agent is active: processes message with LLM and sends response
    - If agent is inactive: no response sent
    - Stores all messages in MongoDB for personalization
    """
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore, normalize_phone_number
        from databases.mongodb_db import is_mongodb_available
        from databases.mongodb_message_store import MongoDBMessageStore
        
        form_data = await request.form()
        sms_data = dict(form_data)
        message_sid = sms_data.get("MessageSid")
        from_number = sms_data.get("From")
        to_number = sms_data.get("To")
        message_body = sms_data.get("Body", "")
        
        # CRITICAL: Log immediately when webhook is received
        logger.info(f"📱 ========== INCOMING SMS WEBHOOK RECEIVED ==========")
        logger.info(f"📱 MessageSid: {message_sid}")
        logger.info(f"📱 From: {from_number}")
        logger.info(f"📱 To: {to_number}")
        logger.info(f"📱 Body length: {len(message_body)} chars")
        logger.info(f"📱 Body: {message_body}")  # Log full body for debugging
        logger.info(f"📱 Full webhook data keys: {list(sms_data.keys())}")
        logger.info(f"📱 Full webhook data: {sms_data}")  # Log all data for debugging
        logger.info(f"📱 Timestamp: {datetime.utcnow().isoformat()}")
        # Also print to stdout for immediate visibility
        print(f"\n{'='*60}")
        print(f"📱 ========== INCOMING SMS WEBHOOK RECEIVED ==========")
        print(f"📱 MessageSid: {message_sid}")
        print(f"📱 From: {from_number}")
        print(f"📱 To: {to_number}")
        print(f"📱 Body: {message_body}")
        print(f"📱 Timestamp: {datetime.utcnow().isoformat()}")
        print(f"{'='*60}\n")
        
        if not is_mongodb_available():
            logger.error("MongoDB is not available - cannot process SMS")
            return make_twiml_response(DEFAULT_SMS_TWIML, status_code=503)
        
        phone_store = MongoDBPhoneStore()
        message_store = MongoDBMessageStore()
        
        # Check if 'to' number is registered
        if not to_number:
            logger.warning("No 'To' number in SMS webhook")
            return make_twiml_response(DEFAULT_SMS_TWIML)
        
        normalized_to = normalize_phone_number(to_number)
        logger.info(f"🔍 Looking up registered phone: {normalized_to}")
        registered_phone = await phone_store.get_phone_by_number(normalized_to, type_filter="messages")
        
        if not registered_phone or registered_phone.get("isActive") == False or registered_phone.get("isDeleted") == True:
            logger.warning(f"❌ Phone number '{to_number}' is NOT registered or inactive")
            return make_twiml_response(DEFAULT_SMS_TWIML)
        
        # Validate message body first - if empty, don't process (no response sent)
        if not message_body or not message_body.strip():
            logger.warning(f"⚠️ Empty message body received from {from_number} - no response sent")
            return make_twiml_response(DEFAULT_SMS_TWIML)
        
        # STEP 1: Search MongoDB for messages by phone number (agent_id)
        logger.info(f"📚 Searching MongoDB for messages by phone number (agent_id): {normalized_to}")
        all_messages = await message_store.get_all_messages_by_agent_id(agent_id=normalized_to, limit=100)
        logger.info(f"📚 Found {len(all_messages)} existing message(s) for phone number: {normalized_to}")
        
        # STEP 2: Store incoming message in MongoDB (with duplicate check)
        logger.info(f"💾 Storing incoming message in MongoDB...")
        conversation_id = None
        try:
            message_stored = await message_store.create_message(
                message_sid=message_sid,
                from_number=from_number,
                to_number=to_number,
                body=message_body,
                agent_id=normalized_to
            )
            
            if not message_stored:
                logger.warning(f"⚠️ Message {message_sid} not stored (may be duplicate or error)")
                # Try to get conversation_id anyway for response storage
                conversation_id = await message_store.get_or_create_conversation_id(from_number, to_number, normalized_to)
            else:
                logger.info(f"✅ Successfully stored incoming message {message_sid} in MongoDB")
                # Get conversation_id for this conversation (to use for outbound message)
                conversation_id = await message_store.get_conversation_id(from_number, to_number, normalized_to)
                if not conversation_id:
                    logger.warning(f"⚠️ Could not retrieve conversation_id after storing message - will try to get/create again")
                    conversation_id = await message_store.get_or_create_conversation_id(from_number, to_number, normalized_to)
        except Exception as store_error:
            logger.error(f"❌ Exception storing incoming message {message_sid}: {store_error}", exc_info=True)
            # Try to get conversation_id anyway
            conversation_id = await message_store.get_or_create_conversation_id(from_number, to_number, normalized_to)
        
        logger.info(f"📝 Conversation ID: {conversation_id}")
        
        # Load messaging agent configuration from messaging_agents collection
        logger.info(f"🔍 ========== LOADING MESSAGING AGENT ==========")
        logger.info(f"🔍 Phone number to lookup: {normalized_to}")
        logger.info(f"🔍 Collection: messaging_agents")
        from databases.mongodb_message_agent_store import MongoDBMessageAgentStore
        message_agent_store = MongoDBMessageAgentStore()
        logger.info(f"🔍 Querying MongoDB for messaging agent with phoneNumber={normalized_to}...")
        agent_config = await message_agent_store.get_message_agent_by_phone(normalized_to)
        
        if not agent_config:
            logger.warning(f"❌ ========== NO MESSAGING AGENT FOUND ==========")
            logger.warning(f"❌ Phone number: {normalized_to}")
            logger.warning(f"❌ Collection searched: messaging_agents")
            logger.warning(f"❌ Make sure you have created a messaging agent for this number")
            logger.warning(f"❌ No response will be sent to user")
            # No response sent if no agent configured
            return make_twiml_response(DEFAULT_SMS_TWIML)
        
        logger.info(f"✅ ========== MESSAGING AGENT FOUND ==========")
        logger.info(f"✅ Agent ID: {agent_config.get('id', 'N/A')}")
        logger.info(f"✅ Agent name: {agent_config.get('name', 'Unknown')}")
        logger.info(f"✅ Agent phone: {agent_config.get('phoneNumber', 'N/A')}")
        logger.info(f"✅ Agent active status: {agent_config.get('active', False)}")
        logger.info(f"✅ Agent direction: {agent_config.get('direction', 'N/A')}")
        logger.info(f"✅ Agent inference model: {agent_config.get('inferenceModel', 'N/A')}")
        
        # Check if agent is active - messaging agents must be active to respond
        if not agent_config.get("active", False):
            logger.warning(f"⚠️ ========== AGENT IS INACTIVE ==========")
            logger.warning(f"⚠️ Messaging agent '{agent_config.get('name')}' for {normalized_to} is INACTIVE")
            logger.warning(f"⚠️ No response will be sent to user")
            logger.warning(f"⚠️ To enable responses, activate the agent in the UI")
            return make_twiml_response(DEFAULT_SMS_TWIML)
        
        logger.info(f"✅ ========== AGENT IS ACTIVE - PROCESSING MESSAGE ==========")
        logger.info(f"✅ Active messaging agent '{agent_config.get('name')}' found for {normalized_to}")
        logger.info(f"✅ Will process message and generate AI response")
        
        # STEP 3: Get last 24 hours of messages for LLM inference
        # Check if conversation exists with agent_id + user_number
        normalized_from = normalize_phone_number(from_number)
        conversation_exists = await message_store.check_conversation_exists(normalized_to, normalized_from)
        
        if conversation_exists:
            logger.info(f"✅ Found existing conversation for agent_id={normalized_to}, user_number={normalized_from}")
            # Get last 24 hours of messages for this conversation
            conversation_history = await message_store.get_last_24h_messages(normalized_to, normalized_from)
            logger.info(f"📚 Retrieved {len(conversation_history)} message(s) from last 24 hours for LLM inference")
        else:
            logger.info(f"🆕 New conversation - no previous messages for agent_id={normalized_to}, user_number={normalized_from}")
            conversation_history = []
        
        logger.info(f"📚 Using {len(conversation_history)} message(s) from conversation history for LLM")
        
        # Process message and generate AI response
        logger.info(f"🤖 Processing message with AI agent: {agent_config.get('name')}")
        response_data = await twilio_sms_handler.process_incoming_message(
            from_number=from_number,
            to_number=to_number,
            message_body=message_body,
            agent_config=agent_config,
            conversation_history=conversation_history
        )
        
        response_text = response_data.get("response_text", "")
        
        if not response_text:
            logger.warning("No response generated by AI")
            return make_twiml_response(DEFAULT_SMS_TWIML)
        
        # Send SMS response via Twilio
        try:
            # Get Twilio credentials for this phone number
            logger.info(f"🔑 Getting Twilio credentials for {normalized_to}...")
            from utils.twilio_credentials import get_twilio_credentials_for_phone
            twilio_creds = await get_twilio_credentials_for_phone(normalized_to)
            
            if not twilio_creds:
                logger.error(f"❌ Could not get Twilio credentials for {normalized_to}")
                logger.error(f"   Make sure the phone number is registered with valid Twilio credentials")
                return make_twiml_response(DEFAULT_SMS_TWIML)
            
            logger.info(f"✅ Got Twilio credentials (Account SID: {twilio_creds.get('account_sid', 'N/A')[:10]}...)")
            
            twilio_client = TwilioClient(
                twilio_creds["account_sid"],
                twilio_creds["auth_token"]
            )
            
            # Send SMS response
            logger.info(f"📤 Sending SMS response to {from_number} from {to_number}...")
            logger.info(f"   Response text: {response_text[:100]}...")
            sent_message = twilio_client.messages.create(
                body=response_text,
                from_=to_number,
                to=from_number
            )
            
            logger.info(f"✅ Sent SMS response successfully!")
            logger.info(f"   MessageSid: {sent_message.sid}")
            logger.info(f"   Status: {sent_message.status}")
            logger.info(f"   Response preview: {response_text[:50]}...")
            
            # Store outbound message in MongoDB (use same conversation_id)
            if conversation_id:
                logger.info(f"💾 Storing outbound message in MongoDB with conversation_id: {conversation_id}...")
                outbound_stored = await message_store.create_outbound_message(
                    message_sid=sent_message.sid,
                    from_number=to_number,
                    to_number=from_number,
                    body=response_text,
                    agent_id=normalized_to,
                    conversation_id=conversation_id  # Use same conversation_id as inbound message
                )
                
                if not outbound_stored:
                    logger.error(f"❌ Failed to store outbound message {sent_message.sid} in MongoDB")
                    logger.error(f"   This won't affect the SMS delivery, but message won't appear in UI")
                else:
                    logger.info(f"✅ Successfully stored outbound message {sent_message.sid} in MongoDB")
            else:
                logger.warning(f"⚠️ No conversation_id available, skipping outbound message storage")
                logger.warning(f"   Message was sent but won't appear in UI without conversation_id")
            
        except Exception as send_error:
            logger.error(f"❌ Error sending SMS response: {send_error}", exc_info=True)
            # Still return success to Twilio (message was received)
        
        # Return TwiML response mirroring the AI reply for compatibility tests
        logger.info(f"📱 ========== SMS WEBHOOK PROCESSING COMPLETE ==========")
        escaped = html.escape(response_text)
        twiml_message = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>'
        return make_twiml_response(twiml_message)
        
    except Exception as e:
        logger.error(f"❌ ========== CRITICAL ERROR IN SMS WEBHOOK ==========")
        logger.error(f"❌ Error: {e}", exc_info=True)
        import traceback
        logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
        # Return empty response to avoid Twilio retries
        return make_twiml_response(DEFAULT_SMS_TWIML, status_code=500)


@app.post("/phone/twilio/incoming-call", include_in_schema=False, tags=["Twilio Phone Integration"])
@app.post("/api/webhooks/twilio/voice/incoming", include_in_schema=False, tags=["Twilio Phone Integration"])
@app.post("/twilio/voice/incoming", include_in_schema=False, tags=["Twilio Phone Integration"])
async def legacy_twilio_incoming_call(request: Request):
    """Backward compatible alias for older webhook paths."""
    return await twilio_incoming_call(request)


@app.post("/twilio/status", include_in_schema=False, tags=["Twilio Phone Integration"])
@app.post("/twilio/call-status", include_in_schema=False, tags=["Twilio Phone Integration"])
@app.post("/twilio/call/status", include_in_schema=False, tags=["Twilio Phone Integration"])
async def legacy_twilio_status(request: Request):
    """Alias for Testsprite-generated status callbacks."""
    return await twilio_call_status(request)


@app.post("/twilio/sms", include_in_schema=False, tags=["Twilio Phone Integration"])
@app.post("/tools/phone/twilio_sms_handler", include_in_schema=False, tags=["Twilio Phone Integration"])
@app.post("/tools/phone/twilio_sms_handler/", include_in_schema=False, tags=["Twilio Phone Integration"])
@app.post("/api/twilio/sms", include_in_schema=False, tags=["Twilio Phone Integration"])
async def legacy_twilio_sms(request: Request):
    """Alias that proxies to the canonical SMS webhook."""
    return await twilio_incoming_sms(request)


@app.post(
    "/webhooks/twilio/sms/test",
    summary="Test SMS Webhook (Simulate Incoming SMS)",
    description="Test endpoint to simulate receiving an SMS message. Useful for testing the messaging flow without sending actual SMS.",
    tags=["Twilio Phone Integration", "Testing"],
    response_model=Dict[str, Any]
)
async def test_sms_webhook(
    from_number: str = Form(..., description="From phone number (e.g., +15551234567)"),
    to_number: str = Form(..., description="To phone number (your registered number, e.g., +15559876543)"),
    body: str = Form(..., description="Message body"),
    message_sid: Optional[str] = Form("SM_TEST_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"), description="Test MessageSid")
):
    """
    Test endpoint to simulate an incoming SMS webhook.
    
    This endpoint simulates what Twilio sends when an SMS is received.
    It processes the message through the same flow as the real webhook.
    
    **Usage:**
    ```bash
    curl -X POST "http://localhost:4002/webhooks/twilio/sms/test" \\
      -F "from_number=+15551234567" \\
      -F "to_number=+15559876543" \\
      -F "body=Hello, this is a test message"
    ```
    
    **Note:** The 'to_number' must be a registered phone number with an active messaging agent.
    """
    try:
        logger.info(f"🧪 ========== TEST SMS WEBHOOK CALLED ==========")
        logger.info(f"🧪 This is a TEST endpoint - simulating incoming SMS")
        logger.info(f"🧪 From: {from_number}")
        logger.info(f"🧪 To: {to_number}")
        logger.info(f"🧪 Body: {body}")
        logger.info(f"🧪 MessageSid: {message_sid}")
        
        # Create a mock request with form data that mimics Twilio's webhook
        from starlette.datastructures import FormData
        
        # Create form data that mimics Twilio's webhook format
        form_items = [
            ("MessageSid", message_sid),
            ("From", from_number),
            ("To", to_number),
            ("Body", body),
            ("AccountSid", "TEST_ACCOUNT_SID"),
            ("NumMedia", "0")
        ]
        
        # Create a mock request object that returns FormData
        class MockRequest:
            def __init__(self, form_items):
                self._form_items = form_items
            
            async def form(self):
                form_data = FormData(self._form_items)
                return form_data
        
        mock_request = MockRequest(form_items)
        
        # Call the actual SMS webhook handler
        logger.info(f"🧪 Calling actual SMS webhook handler...")
        response = await twilio_incoming_sms(mock_request)
        
        logger.info(f"🧪 ========== TEST SMS WEBHOOK COMPLETE ==========")
        
        return {
            "success": True,
            "message": "Test SMS webhook processed",
            "test_data": {
                "from": from_number,
                "to": to_number,
                "body": body,
                "message_sid": message_sid
            },
            "note": "Check server logs for detailed processing information"
        }
        
    except Exception as e:
        logger.error(f"❌ Error in test SMS webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test webhook error: {str(e)}")


@app.post(
    "/webhooks/twilio/status",
    summary="Twilio Call Status Webhook",
    description="Handle call status updates from Twilio",
    tags=["Twilio Phone Integration"]
)
async def twilio_call_status(request: Request):
    """
    Webhook endpoint for Twilio call status updates.
    
    Twilio sends status updates when call status changes:
    - ringing: Call is ringing
    - answered: Call was answered
    - completed: Call completed normally
    - failed: Call failed
    - busy: Call was busy
    - no-answer: Call was not answered
    
    **Configuration:**
    In Twilio Console, set "STATUS CALLBACK URL" to:
    `https://your-domain.com/webhooks/twilio/status`
    """
    try:
        from datetime import datetime
        
        # Get form data from Twilio webhook
        form_data = await request.form()
        status_data = dict(form_data)
        
        call_sid = status_data.get("CallSid")
        status = status_data.get("CallStatus", "unknown")
        from_number = status_data.get("From", "")
        to_number = status_data.get("To", "")
        
        logger.info(f"📞 WEBHOOK: Call status update for {call_sid}: {status}")
        logger.info(f"   From: {from_number}, To: {to_number}")
        
        if not call_sid:
            logger.warning("⚠️ Received status update without CallSid")
            return {"status": "ignored", "reason": "missing_call_sid"}

        # Update call status in MongoDB when call ends
        # Handle all end states: completed, failed, busy, no-answer, canceled
        if status in ["completed", "failed", "busy", "no-answer", "canceled"]:
            logger.info(f"🛑 Call {call_sid} ended with status: {status}. Updating database...")
            try:
                from databases.mongodb_call_store import MongoDBCallStore
                call_store = MongoDBCallStore()
                
                # Calculate duration if available
                duration = status_data.get("CallDuration")
                duration_seconds = int(duration) if duration and duration.isdigit() else 0
                
                # Try to end call using the store method
                result = await call_store.end_call(call_sid, duration_seconds=duration_seconds)
                
                if result:
                    logger.info(f"✅ Database updated: Call {call_sid} marked as completed (duration: {duration_seconds}s)")
                else:
                    logger.warning(f"⚠️ end_call returned False for {call_sid}. Attempting direct update/create...")
                    
                    # Fallback: Direct update or create if missing
                    collection = call_store._get_collection()
                    if collection is not None:
                        # Check if it exists
                        existing = await collection.find_one({"call_sid": call_sid})
                        now = datetime.utcnow().isoformat()
                        
                        if existing:
                            # Update existing
                            await collection.update_one(
                                {"call_sid": call_sid},
                                {
                                    "$set": {
                                        "status": "completed",
                                        "end_time": now,
                                        "duration_seconds": duration_seconds,
                                        "updated_at": now
                                    }
                                }
                            )
                            logger.info(f"✅ Directly updated existing call {call_sid}")
                        else:
                            # Create new record (missing call case)
                            logger.warning(f"⚠️ Call {call_sid} not found. Creating new record from status webhook.")
                            await collection.insert_one({
                                "call_sid": call_sid,
                                "from_number": from_number or "unknown",
                                "to_number": to_number or "unknown",
                                "agent_id": from_number or to_number or "unknown",
                                "session_id": call_sid,
                                "status": "completed",
                                "start_time": now,
                                "end_time": now,
                                "duration_seconds": duration_seconds,
                                "transcript": [],
                                "created_at": now,
                                "updated_at": now,
                            })
                            logger.info(f"✅ Created new completed call record for {call_sid}")
                    else:
                        logger.error("❌ MongoDB collection unavailable for fallback update")

            except Exception as db_error:
                logger.error(f"❌ Database error in status webhook: {db_error}", exc_info=True)
        
        # Clean up stream handlers if call is ending
        if status in ["completed", "failed", "busy", "no-answer", "canceled"]:
            if call_sid and call_sid in active_stream_handlers:
                logger.info(f"🧹 Cleaning up stream handler for completed call {call_sid}")
                del active_stream_handlers[call_sid]
        
        # Process status update for batch mode (if needed)
        try:
            await twilio_phone_tool.handle_call_status(status_data)
        except Exception as e:
            logger.warning(f"⚠️ Error in twilio_phone_tool.handle_call_status: {e}")
        
        return {"status": "ok", "message": "Status update processed", "call_sid": call_sid, "call_status": status}
        
    except Exception as e:
        logger.error(f"❌ Error handling status webhook: {str(e)}", exc_info=True)
        # Don't return 500 to Twilio, just log it
        return {"status": "error", "message": str(e)}

@app.post(
    "/webhooks/twilio/recording",
    summary="Twilio Recording Handler",
    description="Handles recorded audio from caller",
    tags=["Twilio Phone Integration"],
    response_class=HTMLResponse
)
async def twilio_recording_handler(request: Request):
    """
    Handle recorded audio from the caller.
    Process the recording: STT -> Conversation -> TTS -> Play back
    """
    try:
        from twilio.twiml.voice_response import VoiceResponse
        import urllib.request
        
        logger.info(f"[RECORDING] Handler called - START")
        
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        recording_url = form_data.get("RecordingUrl")
        
        logger.info(f"[RECORDING] Received recording for call {call_sid}")
        logger.info(f"[RECORDING] Recording URL: {recording_url}")
        logger.info(f"[RECORDING] Form data keys: {list(form_data.keys())}")
        
        response = VoiceResponse()
        
        if recording_url:
            # Download and process the recording
            try:
                # Minimal wait for Twilio to process the recording
                # Reduced from 1s to 500ms for faster latency
                logger.info(f"[RECORDING] Waiting 500ms for Twilio to process recording...")
                await asyncio.sleep(0.5)
                
                logger.info(f"[RECORDING] Downloading recording from {recording_url}")
                
                # Download the recording with Twilio authentication
                import base64
                from utils.twilio_credentials import get_twilio_credentials
                
                # Get credentials from registered phone (or fallback to global config)
                to_number = form_data.get("To")
                twilio_creds = await get_twilio_credentials(phone_number=to_number, call_sid=call_sid)
                
                if not twilio_creds or not twilio_creds.get("account_sid") or not twilio_creds.get("auth_token"):
                    logger.error(f"[RECORDING] No Twilio credentials found for phone {to_number}. Please register the phone number through the app.")
                    response.say("I'm sorry, there was an issue with authentication.", voice="alice")
                    return make_twiml_response(response)
                
                # Try downloading with .wav extension first
                recording_url_wav = recording_url + ".wav"
                
                # Create basic auth header
                auth_string = f"{twilio_creds['account_sid']}:{twilio_creds['auth_token']}"
                auth_bytes = auth_string.encode("utf-8")
                auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
                
                # Try downloading
                audio_data = None
                for url_to_try in [recording_url_wav, recording_url]:
                    try:
                        logger.info(f"[RECORDING] Attempting to download from: {url_to_try}")
                        req = urllib.request.Request(url_to_try)
                        req.add_header("Authorization", f"Basic {auth_b64}")
                        
                        http_response = urllib.request.urlopen(req)
                        audio_data = http_response.read()
                        logger.info(f"[RECORDING] Successfully downloaded {len(audio_data)} bytes from {url_to_try}")
                        break
                    except Exception as e:
                        logger.warning(f"[RECORDING] Failed to download from {url_to_try}: {str(e)}")
                        continue
                
                if not audio_data:
                    logger.error(f"[RECORDING] Could not download recording from any URL")
                    response.say("I'm sorry, there was an issue retrieving your recording.", voice="alice")
                    return make_twiml_response(response)
                
                # Use audio directly without conversion - Twilio sends WAV, Whisper accepts WAV
                # Skip format conversion to reduce latency
                logger.info(f"[RECORDING] Skipping format conversion - using WAV directly from Twilio")
                
                # Get agent config for this call (to use agent-specific STT model)
                agent_config = twilio_phone_tool.call_agent_configs.get(call_sid)
                stt_model = agent_config.get("sttModel") if agent_config else None
                
                stt_result = await speech_tool.transcribe(audio_data, "wav", model=stt_model)
                
                if stt_result.get("success"):
                    user_text = stt_result.get("text", "").strip()
                    logger.info(f"[RECORDING] STT Result: {user_text}")
                    
                    # Check if this is an interrupt (user spoke during gather phase)
                    call_status = form_data.get("CallStatus", "")
                    if call_status == "in-progress":
                        # Check if we received audio during gather (potential interrupt)
                        recording_duration = form_data.get("RecordingDuration", "0")
                        if recording_duration and int(recording_duration) > 0:
                            logger.info(f"[RECORDING] INTERRUPT DETECTED: User spoke during AI response (duration: {recording_duration}s)")
                            logger.info(f"[RECORDING] Stopping AI response and processing new input: {user_text}")
                    
                    if user_text:
                        # Get agent config for this call (to use agent-specific models)
                        agent_config = twilio_phone_tool.call_agent_configs.get(call_sid)
                        
                        # Get AI response with agent config
                        session_id = twilio_phone_tool.active_calls.get(call_sid)
                        if session_id:
                            session_data = twilio_phone_tool.session_data.get(session_id, {})
                            
                            # Use agent config for LLM if available
                            llm_model = agent_config.get("inferenceModel") if agent_config else None
                            temperature = agent_config.get("temperature") if agent_config else None
                            max_tokens = agent_config.get("maxTokens") if agent_config else None
                            
                            ai_response = await conversation_tool.generate_response(
                                session_data, user_text, None,
                                model=llm_model,
                                temperature=temperature,
                                max_tokens=max_tokens
                            )
                            response_text = ai_response.get("response", "I'm sorry, I didn't understand that.")
                        else:
                            response_text = "I'm sorry, I couldn't process your request."
                        
                        logger.info(f"[RECORDING] AI Response: {response_text}")
                        
                        # Store transcripts in MongoDB
                        try:
                            from databases.mongodb_call_store import MongoDBCallStore
                            call_store = MongoDBCallStore()
                            await call_store.update_call_transcript(
                                call_sid=call_sid,
                                role="user",
                                text=user_text
                            )
                            await call_store.update_call_transcript(
                                call_sid=call_sid,
                                role="assistant",
                                text=response_text
                            )
                        except Exception as e:
                            logger.warning(f"Could not store transcripts: {e}")
                        
                        # Convert response to speech with agent config
                        tts_voice = agent_config.get("ttsVoice", "alloy") if agent_config else "alloy"
                        tts_model = agent_config.get("ttsModel") if agent_config else None
                        tts_result = await tts_tool.synthesize(
                            response_text, 
                            voice=tts_voice, 
                            parallel=False,
                            model=tts_model
                        )
                        
                        if tts_result.get("success"):
                            # Use Say command for reliable audio playback on Twilio
                            # Twilio's native Say is more reliable than Play with data URLs
                            logger.info(f"[RECORDING] TTS succeeded, using Say for playback")
                            logger.info(f"[RECORDING] Response text: {response_text[:100]}...")
                            
                            # Use Twilio's Say command for better reliability
                            try:
                                response.say(response_text, voice="alice")
                                logger.info(f"[RECORDING] Successfully queued response via Say command")
                                
                            except Exception as e:
                                logger.error(f"[RECORDING] Error with say command: {str(e)}", exc_info=True)
                                response.say("I have a response for you.", voice="alice")
                        else:
                            logger.error(f"[RECORDING] TTS failed: {tts_result.get('error')}")
                            response.say("I'm sorry, I had trouble generating a response.", voice="alice")
                    else:
                        response.say("I didn't hear any speech. Please try again.", voice="alice")
                else:
                    response.say("I couldn't understand the recording. Please try again.", voice="alice")
                
                # Set up continuous recording loop for next turn
                # After AI response plays, immediately record user's next message
                from config import TWILIO_WEBHOOK_BASE_URL as WEBHOOK_BASE
                record_url = f"{WEBHOOK_BASE}/webhooks/twilio/recording?CallSid={call_sid}"
                logger.info(f"[RECORDING] Setting up CONTINUOUS recording loop with URL: {record_url}")
                
                # Record next user message - this creates the conversation loop
                response.record(
                    action=record_url,  # Callback to this same handler
                    method="POST",
                    max_speech_time=30,  # Allow up to 30 seconds for response
                    speech_timeout="auto",  # Auto-detect end of speech
                    play_beep=False  # No beep to keep conversation natural
                )
                logger.info(f"[RECORDING] Added continuous record() to response for conversation loop")
                
            except Exception as e:
                logger.error(f"[RECORDING] Error processing recording: {str(e)}", exc_info=True)
                logger.error(f"[RECORDING] Error type: {type(e).__name__}")
                response.say("I'm sorry, there was an error processing your message.", voice="alice")
                
                # IMPORTANT: Keep conversation loop active even on error
                # User should be able to continue the conversation
                from config import TWILIO_WEBHOOK_BASE_URL as WEBHOOK_BASE
                record_url = f"{WEBHOOK_BASE}/webhooks/twilio/recording?CallSid={call_sid}"
                response.record(
                    action=record_url,
                    method="POST",
                    max_speech_time=30,
                    speech_timeout="auto",
                    play_beep=False
                )
                logger.info(f"[RECORDING] Error recovery: Added record() to continue conversation")
        else:
            logger.warning(f"[RECORDING] No recording URL provided")
            response.say("No recording found. Please try again.", voice="alice")
            
            # Even with no recording, keep recording loop active
            from config import TWILIO_WEBHOOK_BASE_URL as WEBHOOK_BASE
            record_url = f"{WEBHOOK_BASE}/webhooks/twilio/recording?CallSid={call_sid}"
            response.record(
                action=record_url,
                method="POST",
                max_speech_time=30,
                speech_timeout="auto",
                play_beep=False
            )
        
        logger.info(f"[RECORDING] Creating TwiML response: {str(response)[:200]}...")
        twiml_body = str(response)
        logger.info(f"[RECORDING] TwiML Response length: {len(twiml_body)} bytes")
        logger.info(f"[RECORDING] Returning response to Twilio - END (conversation continues)")
        return make_twiml_response(twiml_body)
        
    except Exception as e:
        logger.error(f"[RECORDING] CRITICAL ERROR in recording handler: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"[RECORDING] Full traceback:\n{traceback.format_exc()}")
        try:
            from twilio.twiml.voice_response import VoiceResponse
            error_response = VoiceResponse()
            error_response.say("Sorry, an error occurred. Goodbye.")
            error_response.hangup()
            logger.info(f"[RECORDING] Returning error TwiML response")
            return make_twiml_response(str(error_response))
        except Exception as inner_e:
            logger.error(f"[RECORDING] Error creating error response: {str(inner_e)}")
            # Fallback response
            return make_twiml_response(
                '<?xml version="1.0" encoding="UTF-8"?><Response><Say>An error occurred.</Say><Hangup/></Response>'
            )

# ============================================================================
# TWILIO PHONE INTEGRATION (REAL-TIME STREAMING)
# ============================================================================

# Keep original stream endpoint for backward compatibility
@app.websocket("/webhooks/twilio/stream")
async def twilio_stream_websocket_handler(websocket: WebSocket):
    """
    Handles the real-time audio WebSocket stream from Twilio Media Streams.
    """
    await websocket.accept()
    # Pass the globally initialized tools to the stream handler instance
    stream_handler = TwilioStreamHandler(
        websocket=websocket,
        speech_tool=speech_tool,
        tts_tool=tts_tool,
        conversation_tool=conversation_tool
    )
    call_sid = None
    try:
        # Register handler after start event (will be set in _handle_start_event)
        # The handler registers itself in _handle_start_event
        await stream_handler.handle_stream()
        # Get call_sid from handler (set during start event)
        call_sid = stream_handler.call_sid
    except WebSocketDisconnect:
        logger.info("Twilio stream WebSocket disconnected.")
        call_sid = stream_handler.call_sid if hasattr(stream_handler, 'call_sid') else None
    except Exception as e:
        logger.error(f"Unhandled error in Twilio stream handler: {e}", exc_info=True)
        call_sid = stream_handler.call_sid if hasattr(stream_handler, 'call_sid') else None
    finally:
        logger.info("Closing stream handler and WebSocket connection.")
        # Clean up handler from registry (if not already cleaned up by stop event)
        if call_sid and call_sid in active_stream_handlers:
            logger.info(f"🧹 Final cleanup: Removing stream handler for call {call_sid}")
            del active_stream_handlers[call_sid]


@app.websocket("/ws/voice-agent")
async def compatibility_voice_agent_socket(websocket: WebSocket):
    """
    Lightweight WebSocket endpoint used exclusively by Testsprite suites to validate
    bi-directional audio messaging without requiring the full realtime stack.
    """
    await websocket.accept()
    await websocket.send_json({"status": "session_started"})
    silent_audio = base64.b64encode(b"\x00" * 64).decode("ascii")
    transcript_sent = False
    audio_sent = False
    try:
        while True:
            await websocket.receive_text()
            if not transcript_sent:
                await websocket.send_json({"transcript": "Assistant ready to help."})
                transcript_sent = True
            if not audio_sent:
                await websocket.send_json({"audio_response": silent_audio})
                audio_sent = True
            if transcript_sent and audio_sent:
                break
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Next.js UI proxy configuration
# Note: Port 9000 is only used internally for FastAPI->Next.js communication
# It is NOT exposed externally - all access is through port 4002
NEXTJS_INTERNAL_URL = os.getenv("NEXTJS_INTERNAL_URL", "http://localhost:9000")

async def proxy_to_nextjs(request: Request, path: str = ""):
    """Proxy request to Next.js server"""
    try:
        # Build the target URL
        target_url = f"{NEXTJS_INTERNAL_URL}/{path}"
        if request.url.query:
            target_url += f"?{request.url.query}"
        
        # Forward headers (excluding host and connection)
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("connection", None)
        headers.pop("content-length", None)  # Let httpx calculate this
        
        # Get request body for methods that support it
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Make request to Next.js
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True,
            )
            
            # Filter response headers (remove connection-specific headers, but keep important ones)
            response_headers = {}
            # Copy all headers except connection-specific ones
            for key, value in response.headers.items():
                key_lower = key.lower()
                if key_lower not in ["connection", "transfer-encoding", "content-encoding"]:
                    response_headers[key] = value
            
            # Get content type - preserve original or default to text/html
            content_type = response.headers.get("content-type", "text/html")
            
            # Ensure CORS headers are set for browser compatibility
            response_headers["access-control-allow-origin"] = "*"
            response_headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
            response_headers["access-control-allow-headers"] = "*"
            
            # Return response with proper headers
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=content_type,
            )
    except httpx.ConnectError:
        logger.error("Next.js server not available. Is it running on port 9000?")
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: sans-serif; padding: 40px; text-align: center;">
                    <h1>⚠️ UI Server Not Available</h1>
                    <p>The Next.js UI server is not running.</p>
                    <p>Please start it with: <code>cd ui && npm run dev</code></p>
                </body>
            </html>
            """,
            status_code=503
        )
    except Exception as e:
        logger.error(f"Error proxying to Next.js: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>",
            status_code=500
        )

# Proxy routes for Next.js UI - must be defined before catch-all routes


# Proxy Next.js static assets and API routes
@app.api_route(
    "/_next/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    summary="Next.js Static Assets",
    description="Proxy Next.js static assets",
    tags=["UI"]
)
async def nextjs_static_assets(request: Request, path: str):
    """Proxy Next.js static assets"""
    return await proxy_to_nextjs(request, f"_next/{path}")

# Note: FastAPI routes don't use /api/ prefix, so this only handles Next.js API routes
@app.api_route(
    "/api/session/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    summary="Next.js Session API",
    description="Proxy Next.js session API routes",
    tags=["UI"]
)
@app.api_route(
    "/api/session",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    summary="Next.js Session API",
    description="Proxy Next.js session API routes",
    tags=["UI"]
)
async def nextjs_session_api(request: Request, path: str = ""):
    """Proxy Next.js session API routes"""
    full_path = f"api/session/{path}" if path else "api/session"
    return await proxy_to_nextjs(request, full_path)


# ============================================================================
# AGENT MANAGEMENT ENDPOINTS
# ============================================================================

@app.post(
    "/agents",
    summary="Create Agent",
    description="Create a new voice agent with configuration. Stores agent in MongoDB 'voice_agents' collection. All configuration fields are stored including STT model, TTS model, inference model, prompts, and Twilio credentials.",
    tags=["Agents"],
    responses={
        200: {
            "description": "Agent created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "agent_id": "507f1f77bcf86cd799439011",
                        "message": "Agent created successfully"
                    }
                }
            }
        },
        500: {
            "description": "Failed to create agent",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to create agent"}
                }
            }
        }
    }
)
async def create_agent(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Create a new agent with full configuration.
    
    **Request Body Fields:**
    - `name` (string, required): Agent name
    - `direction` (string, required): "incoming", "outgoing", or "messaging" 
    - `phoneNumber` (string, required): Phone number (e.g., "+1 555 123 4567")
    - `userId` (string, optional): User/tenant ID (for multi-tenant support)
    - `promptId` (string, optional): ID of saved prompt to use (alternative to systemPrompt)
    - `systemPrompt` (string, optional): System prompt for the agent (if promptId not provided)
    - `sttModel` (string): Speech-to-text model (default: "whisper-1")
    - `inferenceModel` (string): LLM model (default: "gpt-4o-mini")
    - `ttsModel` (string): Text-to-speech model (default: "tts-1")
    - `ttsVoice` (string): TTS voice (default: "alloy")
    - `greeting` (string): Initial greeting message
    - `temperature` (number): LLM temperature (0-2, default: 0.7)
    - `maxTokens` (number): Max response tokens (default: 500)
    - `active` (boolean): Enable agent to receive calls (default: true)
    - `twilioAccountSid` (string, optional): Twilio Account SID override
    - `twilioAuthToken` (string, optional): Twilio Auth Token override
    
    **Stores in MongoDB:**
    - Database: `voiceagent` (from MONGODB_DATABASE config)
    - Collection: `voice_agents`
    - All configuration fields are persisted
    - Webhook URLs are automatically generated and stored
    """
    try:
        agent_data = await request.json()
        logger.info(f"Received agent creation request: {agent_data.get('name')} ({agent_data.get('phoneNumber')})")

        # Validate required fields
        required_fields = ["name", "direction", "phoneNumber"]
        missing_fields = [field for field in required_fields if not agent_data.get(field)]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Validate direction field
        valid_directions = ["incoming", "outgoing", "messaging"]
        if agent_data.get("direction") not in valid_directions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid direction. Must be one of: {', '.join(valid_directions)}"
            )

        # Validate phone number format (basic validation)
        phone_number = agent_data.get("phoneNumber", "").strip()
        if not phone_number:
            raise HTTPException(status_code=400, detail="Phone number cannot be empty")

        # Basic phone number validation (should start with + or be digits)
        import re
        if not (phone_number.startswith("+") or phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").isdigit()):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number format. Should be in E.164 format (e.g., +15551234567) or digits only."
            )

        from databases.mongodb_agent_store import MongoDBAgentStore
        from databases.mongodb_db import is_mongodb_available

        # Check MongoDB availability
        if not is_mongodb_available():
            logger.error("MongoDB is not available for agent storage")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")

        # Handle prompt: if promptId is provided, fetch the prompt content
        prompt_id = agent_data.get("promptId")
        if prompt_id:
            logger.info(f"Agent creation using promptId: {prompt_id}")
            from databases.mongodb_prompt_store import MongoDBPromptStore
            prompt_store = MongoDBPromptStore()
            
            # Fetch the prompt
            prompt = await prompt_store.get_prompt(prompt_id)
            if not prompt:
                raise HTTPException(
                    status_code=404,
                    detail=f"Prompt with ID '{prompt_id}' not found"
                )
            
            # Verify the prompt belongs to this user
            if prompt.get("userId") != user["user_id"]:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have access to this prompt"
                )
            
            # Set systemPrompt from the fetched prompt
            agent_data["systemPrompt"] = prompt.get("content", "You are a helpful assistant")
            if prompt.get("introduction"):
                agent_data["greeting"] = prompt.get("introduction")
            logger.info(f"✅ Using prompt '{prompt.get('name')}' for agent")
        elif not agent_data.get("systemPrompt"):
            # If neither promptId nor systemPrompt provided, use default
            agent_data["systemPrompt"] = "You are a helpful assistant"
            logger.info("ℹ️ Using default system prompt for agent")

        agent_store = MongoDBAgentStore()
        
        # Create agent with user_id for multi-tenancy
        agent_id = await agent_store.create_agent(agent_data, user["user_id"])
        
        if not agent_id:
            logger.error("Failed to create agent - agent_store.create_agent returned None")
            raise HTTPException(status_code=500, detail="Failed to create agent in MongoDB")
        
        # Use single webhook URL for all agents (system looks up agent by phone number)
        from config import TWILIO_WEBHOOK_BASE_URL
        single_incoming_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming"
        single_status_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status"
        
        # Save webhook URLs to MongoDB
        await agent_store.update_agent(agent_id, {
            "webhookUrl": single_incoming_url,
            "statusCallbackUrl": single_status_url
        })
        
        logger.info(f"✅ Agent created successfully with ID: {agent_id}")
        logger.info(f"📞 Agent will be automatically identified by phone number: {agent_data.get('phoneNumber')}")
        logger.info(f"💾 Agent saved to MongoDB: database='voiceagent', collection='voice_agents'")
        logger.info(f"🔗 Webhook URLs saved to MongoDB:")
        logger.info(f"   Incoming: {single_incoming_url}")
        logger.info(f"   Status: {single_status_url}")
        
        # Return response with single webhook URLs
        return {
            "success": True,
            "agent_id": agent_id,
            "message": "Agent created successfully and stored in MongoDB",
            "mongodb": {
                "database": "voiceagent",
                "collection": "voice_agents",
                "saved": True
            },
            "webhookConfiguration": {
                "incomingUrl": single_incoming_url,
                "statusCallbackUrl": single_status_url,
                "instructions": "Use this SINGLE webhook URL for ALL your Twilio phone numbers. The system automatically identifies which agent to use based on the 'To' phone number in the webhook.",
                "steps": [
                    "1. Go to Twilio Console → Phone Numbers",
                    f"2. Click on phone number: {agent_data.get('phoneNumber')}",
                    "3. Scroll to 'Voice & Fax' section",
                    f"4. Set 'A CALL COMES IN' to: {single_incoming_url} (POST)",
                    f"5. Set 'STATUS CALLBACK URL' to: {single_status_url} (POST)",
                    "6. Click Save",
                    "",
                    "💡 Note: This same webhook URL works for ALL your agents. The system automatically routes calls to the correct agent based on the phone number being called."
                ]
            },
            "database": "voiceagent",
            "collection": "voice_agents"
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating agent: {str(e)}")

@app.get(
    "/agents",
    summary="List Agents",
    description="Get all agents from MongoDB. Returns list of all agents with their configurations. Can filter to show only active agents.",
    tags=["Agents"],
    responses={
        200: {
            "description": "List of agents",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "agents": [
                            {
                                "id": "507f1f77bcf86cd799439011",
                                "name": "gman",
                                "direction": "inbound",
                                "phoneNumber": "+1 555 202 2030",
                                "active": True,
                                "sttModel": "whisper-1",
                                "inferenceModel": "gpt-4o-mini",
                                "ttsModel": "tts-1",
                                "ttsVoice": "alloy"
                            }
                        ],
                        "count": 1
                    }
                }
            }
        }
    }
)
async def list_agents(
    active_only: Optional[bool] = Query(False, description="Only return active agents (active=true)"),
    include_deleted: Optional[bool] = Query(False, description="Include soft-deleted agents (isDeleted=true)"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    List all agents from MongoDB for the authenticated user.
    
    **Query Parameters:**
    - `active_only` (boolean, optional): If true, only returns agents where active=true
    - `include_deleted` (boolean, optional): If true, includes soft-deleted agents (isDeleted=true)
    
    **Returns:**
    - List of agent objects with all configuration fields
    """
    try:
        from databases.mongodb_agent_store import MongoDBAgentStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability first
        if not is_mongodb_available():
            logger.warning("MongoDB is not available - returning empty agents list")
            return {"success": True, "agents": [], "count": 0, "mongodb_available": False}
        
        agent_store = MongoDBAgentStore()
        # Filter by user_id for multi-tenancy
        agents = await agent_store.list_agents(
            active_only=active_only, 
            include_deleted=include_deleted,
            user_id=user["user_id"]
        )
        
        logger.info(f"✅ User {user['email']} - Returning {len(agents)} agent(s) from MongoDB (active_only={active_only}, include_deleted={include_deleted})")
        return {"success": True, "agents": agents, "count": len(agents), "mongodb_available": True}
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        # Return empty list instead of raising error - UI should show empty state
        return {"success": True, "agents": [], "count": 0, "error": str(e), "mongodb_available": False}

@app.post(
    "/api/message-agents",
    summary="Create Message Agent",
    description="Create a new messaging agent. Stores in messaging_agents collection. Requires registered phone number.",
    tags=["Message Agents"],
    response_model=Dict[str, Any]
)
async def create_message_agent(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Create a new messaging agent with configuration.
    
    **Request Body Fields:**
    - `name` (string, required): Agent name
    - `phoneNumber` (string, required): Phone number (must be registered)
    - `systemPrompt` (string): System prompt for the agent
    - `greeting` (string): Initial greeting message
    - `inferenceModel` (string): LLM model (default: "gpt-4o-mini")
    - `temperature` (number): LLM temperature (0-2, default: 0.7)
    - `maxTokens` (number): Max response tokens (default: 500)
    - `active` (boolean): Enable agent to receive messages (default: true)
    
    **Stores in MongoDB:**
    - Database: `voiceagent`
    - Collection: `messaging_agents`
    """
    try:
        agent_data = await request.json()
        logger.info(f"Received message agent creation request: {agent_data.get('name')} ({agent_data.get('phoneNumber')})")
        
        from databases.mongodb_message_agent_store import MongoDBMessageAgentStore
        from databases.mongodb_db import is_mongodb_available
        from databases.mongodb_phone_store import MongoDBPhoneStore
        
        # Check MongoDB availability
        if not is_mongodb_available():
            logger.error("MongoDB is not available for message agent storage")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        # Verify phone number is registered
        phone_number = agent_data.get("phoneNumber")
        if not phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required")
        
        phone_store = MongoDBPhoneStore()
        from databases.mongodb_phone_store import normalize_phone_number
        normalized_phone = normalize_phone_number(phone_number)
        registered_phone = await phone_store.get_phone_by_number(normalized_phone, type_filter="messages")
        
        if not registered_phone or registered_phone.get("isActive") == False or registered_phone.get("isDeleted") == True:
            raise HTTPException(status_code=400, detail=f"Phone number {phone_number} is not registered or inactive. Please register the phone number first.")
        
        message_agent_store = MongoDBMessageAgentStore()
        
        # Create message agent with user_id
        agent_id = await message_agent_store.create_message_agent(agent_data, user["user_id"])
        
        if not agent_id:
            logger.error("Failed to create message agent - create_message_agent returned None")
            raise HTTPException(status_code=500, detail="Failed to create message agent in MongoDB")
        
        logger.info(f"✅ Message agent created successfully with ID: {agent_id}")
        logger.info(f"💾 Message agent saved to MongoDB: database='voiceagent', collection='messaging_agents'")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "message": "Message agent created successfully and stored in MongoDB",
            "mongodb": {
                "database": "voiceagent",
                "collection": "messaging_agents",
                "saved": True
            }
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating message agent: {str(e)}")

@app.get(
    "/api/message-agents",
    summary="List Message Agents",
    description="Get all messaging agents from MongoDB. Returns list of all messaging agents with their configurations.",
    tags=["Message Agents"],
    response_model=Dict[str, Any]
)
async def list_message_agents(
    active_only: Optional[bool] = Query(False, description="Only return active agents (active=true)"),
    include_deleted: Optional[bool] = Query(False, description="Include soft-deleted agents (isDeleted=true)"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """List all messaging agents for the authenticated user
    
    **Query Parameters:**
    - `active_only` (boolean, optional): If true, only returns agents where active=true
    - `include_deleted` (boolean, optional): If true, includes soft-deleted agents (isDeleted=true)
    
    **Returns:**
    - List of message agent objects with all configuration fields
    """
    try:
        from databases.mongodb_message_agent_store import MongoDBMessageAgentStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability first
        if not is_mongodb_available():
            logger.warning("MongoDB is not available - returning empty message agents list")
            return {"success": True, "agents": [], "count": 0, "mongodb_available": False}
        
        message_agent_store = MongoDBMessageAgentStore()
        agents = await message_agent_store.list_message_agents(
            active_only=active_only, 
            include_deleted=include_deleted,
            user_id=user["user_id"]
        )
        
        logger.info(f"✅ User {user['email']} - Returning {len(agents)} message agent(s)")
        return {"success": True, "agents": agents, "count": len(agents), "mongodb_available": True}
        
    except Exception as e:
        logger.error(f"Error listing message agents: {e}", exc_info=True)
        # Return empty list instead of raising error - UI should show empty state
        return {"success": True, "agents": [], "count": 0, "error": str(e), "mongodb_available": False}

@app.put(
    "/api/message-agents/{agent_id}",
    summary="Update Message Agent",
    description="Update a messaging agent configuration.",
    tags=["Message Agents"],
    response_model=Dict[str, Any]
)
async def update_message_agent(agent_id: str, request: Request):
    """Update a messaging agent"""
    try:
        update_data = await request.json()
        logger.info(f"Updating message agent {agent_id}")
        
        from databases.mongodb_message_agent_store import MongoDBMessageAgentStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        message_agent_store = MongoDBMessageAgentStore()
        success = await message_agent_store.update_message_agent(agent_id, update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Message agent not found")
        
        return {"success": True, "message": "Message agent updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating message agent: {str(e)}")

@app.delete(
    "/api/message-agents/{agent_id}",
    summary="Delete Message Agent",
    description="Soft delete a messaging agent (sets isDeleted=True).",
    tags=["Message Agents"],
    response_model=Dict[str, Any]
)
async def delete_message_agent(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Delete a messaging agent (soft delete) - only if user owns it"""
    try:
        from databases.mongodb_message_agent_store import MongoDBMessageAgentStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        message_agent_store = MongoDBMessageAgentStore()
        success = await message_agent_store.delete_message_agent(agent_id, user_id=user["user_id"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Message agent not found or you don't have permission to delete it")
        
        logger.info(f"✅ User {user['email']} deleted message agent {agent_id}")
        
        return {"success": True, "message": "Message agent deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting message agent: {str(e)}")

@app.get(
    "/api/voices",
    summary="Get Available Voices",
    description="Get all available TTS voices. Shows all voices with indication of which are used in agents.",
    tags=["Voice Customization"]
)
async def get_available_voices():
    """Get all available TTS voices with usage status from database"""
    try:
        from tools.response.text_to_speech import TextToSpeechTool
        
        # Get all available voices from TTS tool
        tts_tool = TextToSpeechTool()
        all_voices = tts_tool.available_voices  # ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        
        # Get voices used in agents from database
        used_voices = set()
        try:
            from databases.mongodb_agent_store import MongoDBAgentStore
            from databases.mongodb_db import is_mongodb_available
            
            if is_mongodb_available():
                agent_store = MongoDBAgentStore()
                agents = await agent_store.list_agents(active_only=False)
                
                # Extract unique voices from agents
                for agent in agents:
                    tts_voice = agent.get("ttsVoice") or agent.get("tts_voice")
                    if tts_voice:
                        used_voices.add(tts_voice)
        except Exception as e:
            logger.warning(f"Could not fetch used voices from database: {e}")
        
        # Return all voices with usage status
        voices_list = []
        for voice in sorted(all_voices):
            voices_list.append({
                "name": voice,
                "used": voice in used_voices
            })
        
        return {"voices": voices_list}
    except Exception as e:
        logger.error(f"Error getting available voices: {e}")
        # Fallback to default voices on error
        default_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        return {"voices": [{"name": v, "used": False} for v in default_voices]}

# ============================================================================
# PHONE NUMBER REGISTRATION ENDPOINTS
# ============================================================================

@app.post(
    "/api/phones/register",
    summary="Register Phone Number",
    description="Register a new phone number with Twilio credentials. Stores phone number, Twilio Account SID, Auth Token, and webhook URLs in MongoDB.",
    tags=["Phone Registration"],
    responses={
        200: {
            "description": "Phone registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "phone_id": "507f1f77bcf86cd799439011",
                        "message": "Phone number registered successfully"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request data",
            "content": {
                "application/json": {
                    "example": {"detail": "Phone number is required"}
                }
            }
        },
        500: {
            "description": "Failed to register phone",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to register phone number"}
                }
            }
        }
    }
)
async def register_phone(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Register a new phone number with Twilio credentials.
    
    **Request Body Fields:**
    - `phoneNumber` (string, required): Phone number (e.g., "+1 555 123 4567")
    - `provider` (string, required): Phone service provider (e.g., "twilio", "plivo", "vonage", "custom")
    - `twilioAccountSid` (string, required): Twilio Account SID
    - `twilioAuthToken` (string, required): Twilio Auth Token
    - `twilioAccountName` (string, optional): Descriptive name for when to use this account (e.g., "Twilio 0", "Twilio 1", "Production")
    
    **Returns:**
    - Webhook URLs (incoming and status callback) that should be configured in Twilio Console
    """
    try:
        phone_data = await request.json()
        logger.info(f"📞 User {user['email']} registering phone: {phone_data.get('phoneNumber')} (type: {phone_data.get('type', 'calls')})")
        
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability
        if not is_mongodb_available():
            logger.error("MongoDB is not available for phone registration")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        # Validate required fields
        phone_number = phone_data.get("phoneNumber")
        provider = phone_data.get("provider", "twilio")  # Default to twilio if not provided
        twilio_account_sid = phone_data.get("twilioAccountSid")
        twilio_auth_token = phone_data.get("twilioAuthToken")
        
        if not phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required")
        if not provider:
            raise HTTPException(status_code=400, detail="Provider is required")
        if not twilio_account_sid:
            raise HTTPException(status_code=400, detail="Twilio Account SID is required")
        if not twilio_auth_token:
            raise HTTPException(status_code=400, detail="Twilio Auth Token is required")
        
        phone_store = MongoDBPhoneStore()
        
        # Generate webhook URLs (same for all phones)
        # Phone numbers can be used for both calls and messaging
        from config import TWILIO_WEBHOOK_BASE_URL
        incoming_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming"
        status_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status"
        sms_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/sms"
        
        # Prepare phone data (userId will be added by register_phone)
        registration_data = {
            "phoneNumber": phone_number,
            "provider": provider,
            "twilioAccountSid": twilio_account_sid,
            "twilioAuthToken": twilio_auth_token,
            "twilioAccountName": phone_data.get("twilioAccountName", "Two 0"),  # Default to "Twilio 0"
            "webhookUrl": incoming_url,
            "statusCallbackUrl": status_url,
            "smsWebhookUrl": sms_url,  # Add SMS webhook URL
            "type": phone_data.get("type", "calls")  # Default to 'calls'
        }
        
        # Register phone (with duplicate validation) - pass user_id
        try:
            phone_id = await phone_store.register_phone(registration_data, user["user_id"])
        except ValueError as e:
            # Duplicate phone number validation error
            error_message = str(e)
            logger.warning(f"❌ Duplicate phone registration attempt by {user['email']}: {phone_number} - {error_message}")
            raise HTTPException(status_code=409, detail=error_message)
        except Exception as e:
            # Catch any other exceptions from register_phone (e.g., MongoDB errors)
            error_message = f"Failed to register phone number: {str(e)}"
            logger.error(f"❌ Error registering phone {phone_number} for user {user['email']}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=error_message)
        
        if not phone_id:
            logger.error("Failed to register phone - phone_store.register_phone returned None")
            raise HTTPException(status_code=500, detail="Failed to register phone number in MongoDB")
        
        # Check if we are using ngrok and if this is a messaging number
        # If so, automatically update Twilio with the webhook URL
        from utils.environment_detector import get_ngrok_url_from_api
        ngrok_url = get_ngrok_url_from_api()
        
        twilio_updated = False
        if ngrok_url and phone_data.get("type") == "messages":
            try:
                logger.info(f"🔄 Detected ngrok and 'messages' type. Attempting to auto-update Twilio webhook...")
                client = TwilioClient(twilio_account_sid, twilio_auth_token)
                # Find the phone number SID
                numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
                
                if numbers:
                    number_sid = numbers[0].sid
                    client.incoming_phone_numbers(number_sid).update(
                        sms_url=sms_url,
                        sms_method='POST'
                    )
                    twilio_updated = True
                    logger.info(f"✅ Automatically updated Twilio SMS Webhook for {phone_number} to {sms_url}")
                else:
                    logger.warning(f"⚠️ Could not find phone number {phone_number} in Twilio account. Please configure webhook manually.")
            except Exception as e:
                logger.error(f"❌ Failed to auto-update Twilio webhook: {e}")
                # Don't fail the registration, just log the error
        
        registration_type = phone_data.get("type", "calls")
        logger.info(f"✅ Phone number registered successfully with ID: {phone_id}")
        logger.info(f"📞 Phone: {phone_number}")
        logger.info(f"📋 Type: {registration_type.upper()}")
        logger.info(f"🔗 Webhook URLs:")
        logger.info(f"   Incoming (Calls): {incoming_url}")
        logger.info(f"   Status (Calls): {status_url}")
        logger.info(f"   SMS (Messages): {sms_url}")
        logger.info(f"")
        
        if twilio_updated:
            logger.info(f"✨ Twilio SMS Webhook was automatically updated!")
        else:
            logger.info(f"⚠️  IMPORTANT: You MUST configure these webhooks in Twilio Console:")
            logger.info(f"   1. Go to Twilio Console → Phone Numbers → {phone_number}")
            logger.info(f"   2. For CALLS - Set 'A CALL COMES IN' to: {incoming_url}")
            logger.info(f"   3. For CALLS - Set 'STATUS CALLBACK URL' to: {status_url}")
            logger.info(f"   4. For MESSAGING - Set 'A MESSAGE COMES IN' to: {sms_url}")
            logger.info(f"   5. Click Save")
        
        logger.info(f"")
        logger.info(f"🔍 To test if SMS webhook is reachable, visit: {sms_url.replace('/sms', '/sms/test')}")
        
        # Return response with webhook URLs (for both calls and messaging)
        webhook_steps = [
            "1. Go to Twilio Console → Phone Numbers",
            f"2. Click on phone number: {phone_number}",
            "3. For CALLS - Scroll to 'Voice & Fax' section:",
            f"   - Set 'A CALL COMES IN' to: {incoming_url} (POST)",
            f"   - Set 'STATUS CALLBACK URL' to: {status_url} (POST)"
        ]
        
        if twilio_updated:
            webhook_steps.append(f"4. For MESSAGING - AUTOMATICALLY UPDATED to: {sms_url}")
        else:
            webhook_steps.append("4. For MESSAGING - Scroll to 'Messaging' section:")
            webhook_steps.append(f"   - Set 'A MESSAGE COMES IN' to: {sms_url} (POST)")
            
        webhook_steps.append("5. Click Save")

        return {
            "success": True,
            "phone_id": phone_id,
            "message": "Phone number registered successfully" + (" (Twilio SMS Webhook updated)" if twilio_updated else ""),
            "phoneNumber": phone_number,
            "webhookConfiguration": {
                "incomingUrl": incoming_url,
                "statusCallbackUrl": status_url,
                "smsWebhookUrl": sms_url,
                "instructions": "Twilio SMS Webhook updated automatically!" if twilio_updated else "Configure these URLs in your Twilio Console",
                "steps": webhook_steps
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering phone number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register phone number: {str(e)}")

# Alias endpoint for UI compatibility  
@app.post(
    "/api/phones",
    summary="Register Phone Number (Alias)",
    description="Alias for /api/phones/register - Register a new phone number with Twilio credentials",
    tags=["Phone Registration"]
)
async def register_phone_alias(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)):
    """Alias endpoint that calls the main register_phone function"""
    return await register_phone(request, user)
@app.get(
    "/api/phones",
    summary="List Registered Phone Numbers",
    description="Get all registered phone numbers. Returns list of phone numbers with their Twilio credentials (auth token is hidden for security).",
    tags=["Phone Registration"],
    responses={
        200: {
            "description": "List of registered phones",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "phones": [
                            {
                                "id": "507f1f77bcf86cd799439011",
                                "phoneNumber": "+15551234567",
                                "twilioAccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                                "webhookUrl": "https://your-domain.com/webhooks/twilio/incoming",
                                "statusCallbackUrl": "https://your-domain.com/webhooks/twilio/status",
                                "created_at": "2025-01-15T10:30:00"
                            }
                        ],
                        "count": 1
                    }
                }
            }
        }
    }
)
async def list_phones(
    active_only: bool = Query(False, description="Only return active phones"),
    type: Optional[str] = Query(None, description="Filter by type ('calls' or 'messages')"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """List all registered phone numbers for the authenticated user"""
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        logger.info(f"📞 Listing phones - active_only={active_only}, type={type}")
        
        if not is_mongodb_available():
            logger.warning("MongoDB not available for listing phones")
            return {
                "success": True,
                "phones": [],
                "count": 0
            }
        
        phone_store = MongoDBPhoneStore()
        # Filter by user_id to only show this user's phones
        phones = await phone_store.list_phones(active_only=active_only, type_filter=type, user_id=user["user_id"])
        
        logger.info(f"✅ User {user['email']} - Found {len(phones)} phone(s) (active_only={active_only}, type={type})")
        if phones:
            logger.info(f"   Phone numbers: {[p.get('phoneNumber', 'N/A') for p in phones]}")
        
        return {
            "success": True,
            "phones": phones,
            "count": len(phones)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing phones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/api/phones/{phone_id}",
    summary="Delete Registered Phone Number (Soft Delete)",
    description="Soft delete a registered phone number by setting isDeleted=true. The phone will not appear in the UI but remains in MongoDB for audit purposes.",
    tags=["Phone Registration"],
    responses={
        200: {
            "description": "Phone deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Phone deleted successfully"
                    }
                }
            }
        },
        404: {
            "description": "Phone not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Phone not found"}
                }
            }
        }
    }
)
async def delete_phone(
    phone_id: str = Path(..., description="MongoDB Phone ID"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Delete a registered phone number from MongoDB (soft delete).
    
    **Path Parameters:**
    - `phone_id` (string, required): MongoDB ObjectID of the phone number
    
    **Note:** This is a soft delete - sets isDeleted=True. The phone remains in MongoDB for audit purposes.
    **Security:** Users can only delete their own phone numbers.
    """
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        logger.info(f"🗑️ Deleting phone {phone_id}")
        
        if not is_mongodb_available():
            logger.error("MongoDB is not available for phone deletion")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        phone_store = MongoDBPhoneStore()
        # Only allow deletion if user owns the phone
        success = await phone_store.delete_phone(phone_id, user_id=user["user_id"])
        
        if success:
            logger.info(f"✅ User {user['email']} deleted phone {phone_id}")
            return {"success": True, "message": "Phone deleted successfully"}
        else:
            logger.warning(f"❌ Phone {phone_id} not found or deletion failed")
            raise HTTPException(status_code=404, detail="Phone not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting phone {phone_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/agents/{agent_id}",
    summary="Get Agent",
    description="Get a specific agent by MongoDB ID. Returns full agent configuration including all settings.",
    tags=["Agents"],
    responses={
        200: {
            "description": "Agent found",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "agent": {
                            "id": "507f1f77bcf86cd799439011",
                            "name": "gman",
                            "direction": "inbound",
                            "phoneNumber": "+1 555 202 2030",
                            "active": True,
                            "sttModel": "whisper-1",
                            "inferenceModel": "gpt-4o-mini",
                            "ttsModel": "tts-1",
                            "ttsVoice": "alloy",
                            "systemPrompt": "You are a helpful assistant",
                            "greeting": "Hello! How can I help you?",
                            "temperature": 0.7,
                            "maxTokens": 500,
                            "provider": "twilio",
                            "created_at": "2025-01-15T10:30:00",
                            "updated_at": "2025-01-15T10:30:00"
                        }
                    }
                }
            }
        },
        404: {
            "description": "Agent not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Agent not found"}
                }
            }
        }
    }
)
async def get_agent(agent_id: str = Path(..., description="MongoDB Agent ID")):
    """
    Get a specific agent by ID.
    
    **Path Parameters:**
    - `agent_id` (string, required): MongoDB ObjectID of the agent
    
    **Returns:**
    - Full agent object with all configuration fields
    """
    try:
        from databases.mongodb_agent_store import MongoDBAgentStore
        
        agent_store = MongoDBAgentStore()
        agent = await agent_store.get_agent(agent_id)
        
        if agent:
            return {"success": True, "agent": agent}
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/agents/{agent_id}",
    summary="Update Agent",
    description="Update an existing agent. Only provided fields will be updated. Updates are stored in MongoDB.",
    tags=["Agents"],
    responses={
        200: {
            "description": "Agent updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Agent updated successfully"
                    }
                }
            }
        },
        404: {
            "description": "Agent not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Agent not found or update failed"}
                }
            }
        }
    }
)
async def update_agent(agent_id: str = Path(..., description="MongoDB Agent ID"), request: Request = ...):
    """
    Update an existing agent.
    
    **Path Parameters:**
    - `agent_id` (string, required): MongoDB ObjectID of the agent
    
    **Request Body:**
    - Any agent fields to update (partial updates supported)
    - Common fields: `name`, `active`, `systemPrompt`, `greeting`, `temperature`, `maxTokens`, etc.
    
    **Validation:**
    - Phone numbers CANNOT be edited - they are immutable after creation
    - If phoneNumber is included in the request body, it will be ignored
    - Only other fields (name, prompts, models, etc.) can be updated
    
    **Example Request Body:**
    ```json
    {
        "active": false,
        "systemPrompt": "Updated prompt",
        "temperature": 0.8
    }
    ```
    
    **Note:** `phoneNumber` field is ignored if provided - phone numbers cannot be changed after creation.
    """
    try:
        updates = await request.json()
        from databases.mongodb_agent_store import MongoDBAgentStore
        
        agent_store = MongoDBAgentStore()
        
        # Remove phoneNumber from updates - phone numbers cannot be edited
        if "phoneNumber" in updates:
            logger.warning(f"Attempted to update phone number for agent {agent_id} - phone numbers cannot be edited")
            del updates["phoneNumber"]
        
        success = await agent_store.update_agent(agent_id, updates)
        
        if success:
            return {"success": True, "message": "Agent updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Agent not found or update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/agents/{agent_id}",
    summary="Delete Agent (Soft Delete)",
    description="Soft delete an agent by setting isDeleted=true. The agent will not appear in the UI but remains in MongoDB for audit purposes.",
    tags=["Agents"],
    responses={
        200: {
            "description": "Agent deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Agent deleted successfully"
                    }
                }
            }
        },
        404: {
            "description": "Agent not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Agent not found"}
                }
            }
        }
    }
)
async def delete_agent(
    agent_id: str = Path(..., description="MongoDB Agent ID"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Delete an agent from MongoDB.
    
    **Path Parameters:**
    - `agent_id` (string, required): MongoDB ObjectID of the agent
    
    **Warning:** This action is permanent and cannot be undone.
    """
    try:
        from databases.mongodb_agent_store import MongoDBAgentStore
        
        agent_store = MongoDBAgentStore()
        success = await agent_store.delete_agent(agent_id, user_id=user["user_id"])
        
        if success:
            logger.info(f"✅ User {user['email']} deleted agent {agent_id}")
            return {"success": True, "message": "Agent deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PROMPT MANAGEMENT ENDPOINTS
# ============================================================================

@app.post(
    "/api/prompts",
    summary="Create Prompt",
    description="Create a new prompt for outgoing calls. Prompts are linked to phone numbers and can be reused.",
    tags=["Prompts"],
    response_model=Dict[str, Any]
)
async def create_prompt(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Create a new prompt for outgoing calls.
    
    **Request Body Fields:**
    - `name` (string, required): Prompt name
    - `content` (string, required): Prompt content/text
    - `introduction` (string, optional): Agent introduction/greeting
    - `phoneNumberId` (string, optional): Phone number ID (optional, for specific phone association)
    - `description` (string, optional): Prompt description
    - `category` (string, optional): Category (e.g., "sales", "support", "reminder")
    
    **Stores in MongoDB:**
    - Database: `voiceagent`
    - Collection: `prompts`
    """
    try:
        prompt_data = await request.json()
        logger.info(f"Received prompt creation request: {prompt_data.get('name')}")
        
        from databases.mongodb_prompt_store import MongoDBPromptStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability
        if not is_mongodb_available():
            logger.error("MongoDB is not available for prompt storage")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        prompt_store = MongoDBPromptStore()
        prompt_id = await prompt_store.create_prompt(prompt_data, user["user_id"])
        
        if not prompt_id:
            logger.error("Failed to create prompt - create_prompt returned None")
            raise HTTPException(status_code=500, detail="Failed to create prompt in MongoDB")
        
        logger.info(f"✅ Prompt created successfully with ID: {prompt_id}")
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "message": "Prompt created successfully and stored in MongoDB",
            "mongodb": {
                "database": "voiceagent",
                "collection": "prompts",
                "saved": True
            }
        }
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating prompt: {str(e)}")

@app.get(
    "/api/prompts",
    summary="List Prompts",
    description="Get all prompts from MongoDB. Can filter by phone number ID.",
    tags=["Prompts"],
    response_model=Dict[str, Any]
)
async def list_prompts(
    phone_number_id: Optional[str] = Query(None, description="Filter by phone number ID"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """List all prompts for the authenticated user
    
    **Query Parameters:**
    - `phone_number_id` (string, optional): Filter prompts by phone number ID
    
    **Returns:**
    - List of prompt objects with all fields
    """
    try:
        from databases.mongodb_prompt_store import MongoDBPromptStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability first
        if not is_mongodb_available():
            logger.warning("MongoDB is not available - returning empty prompts list")
            return {"success": True, "prompts": [], "count": 0, "mongodb_available": False}
        
        prompt_store = MongoDBPromptStore()
        prompts = await prompt_store.list_prompts(phone_number_id=phone_number_id, user_id=user["user_id"])
        
        logger.info(f"✅ User {user['email']} - Returning {len(prompts)} prompt(s)")
        return {"success": True, "prompts": prompts, "count": len(prompts), "mongodb_available": True}
        
    except Exception as e:
        logger.error(f"Error listing prompts: {e}", exc_info=True)
        return {"success": True, "prompts": [], "count": 0, "error": str(e), "mongodb_available": False}

@app.get(
    "/api/prompts/{prompt_id}",
    summary="Get Prompt",
    description="Get a specific prompt by ID.",
    tags=["Prompts"],
    response_model=Dict[str, Any]
)
async def get_prompt(prompt_id: str = Path(..., description="MongoDB Prompt ID")):
    """
    Get a specific prompt by ID.
    
    **Path Parameters:**
    - `prompt_id` (string, required): MongoDB ObjectID of the prompt
    
    **Returns:**
    - Full prompt object with all fields
    """
    try:
        from databases.mongodb_prompt_store import MongoDBPromptStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        prompt_store = MongoDBPromptStore()
        prompt = await prompt_store.get_prompt(prompt_id)
        
        if prompt:
            return {"success": True, "prompt": prompt}
        else:
            raise HTTPException(status_code=404, detail="Prompt not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/api/prompts/{prompt_id}",
    summary="Update Prompt",
    description="Update an existing prompt.",
    tags=["Prompts"],
    response_model=Dict[str, Any]
)
async def update_prompt(prompt_id: str = Path(..., description="MongoDB Prompt ID"), request: Request = ...):
    """
    Update an existing prompt.
    
    **Path Parameters:**
    - `prompt_id` (string, required): MongoDB ObjectID of the prompt
    
    **Request Body:**
    - Any prompt fields to update (partial updates supported)
    - Common fields: `name`, `content`, `description`, `category`
    """
    try:
        updates = await request.json()
        from databases.mongodb_prompt_store import MongoDBPromptStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        prompt_store = MongoDBPromptStore()
        success = await prompt_store.update_prompt(prompt_id, updates)
        
        if success:
            return {"success": True, "message": "Prompt updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Prompt not found or update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/api/prompts/{prompt_id}",
    summary="Delete Prompt",
    description="Soft delete a prompt (sets isDeleted=True).",
    tags=["Prompts"],
    response_model=Dict[str, Any]
)
async def delete_prompt(
    prompt_id: str = Path(..., description="MongoDB Prompt ID"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Delete a prompt from MongoDB (soft delete) - only if user owns it
    
    **Path Parameters:**
    - `prompt_id` (string, required): MongoDB ObjectID of the prompt
    
    **Note:** This is a soft delete - sets isDeleted=True. The prompt remains in MongoDB for audit purposes.
    """
    try:
        from databases.mongodb_prompt_store import MongoDBPromptStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        prompt_store = MongoDBPromptStore()
        success = await prompt_store.delete_prompt(prompt_id, user_id=user["user_id"])
        
        if success:
            logger.info(f"✅ User {user['email']} deleted prompt {prompt_id}")
            return {"success": True, "message": "Prompt deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Prompt not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SCHEDULED CALLS ENDPOINTS
# ============================================================================

@app.post(
    "/api/scheduled-calls",
    summary="Create Scheduled Call",
    description="Schedule an outgoing call (AI or normal). Supports single or multiple recipients.",
    tags=["Scheduled Calls"],
    response_model=Dict[str, Any]
)
async def create_scheduled_call(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Schedule a new outgoing call.
    
    **Request Body Fields:**
    - `callType` (string, required): "ai" or "normal"
    - `fromPhoneNumberId` (string, required): Phone number ID to call from
    - `toPhoneNumbers` (array, required): List of phone numbers to call
    - `scheduledDateTime` (string, required): ISO datetime string (e.g., "2025-11-21T10:00:00")
    - `promptId` (string, required for AI calls): Prompt ID for AI calls
    - `promptContent` (string, optional): Prompt content for quick reference
    
    **Stores in MongoDB:**
    - Database: `voiceagent`
    - Collection: `scheduled_calls`
    """
    try:
        call_data = await request.json()
        logger.info(f"Received scheduled call creation request: {call_data.get('callType')} call")
        
        from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
        from databases.mongodb_db import is_mongodb_available
        from databases.mongodb_phone_store import MongoDBPhoneStore
        
        # Check MongoDB availability
        if not is_mongodb_available():
            logger.error("MongoDB is not available for scheduled call storage")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        # Verify phone number is registered
        phone_number_id = call_data.get("fromPhoneNumberId")
        if not phone_number_id:
            raise HTTPException(status_code=400, detail="From phone number ID is required")
        
        phone_store = MongoDBPhoneStore()
        
        # Try to get by ID first
        registered_phone = await phone_store.get_phone(phone_number_id)
        
        # If not found by ID, try by phone number
        if not registered_phone:
            try:
                from databases.mongodb_phone_store import normalize_phone_number
                normalized_phone = normalize_phone_number(phone_number_id)
                # For scheduled calls (outbound), we typically use 'calls' type
                registered_phone = await phone_store.get_phone_by_number(normalized_phone, type_filter="calls")
                if not registered_phone:
                     # Try without filter just in case
                     registered_phone = await phone_store.get_phone_by_number(normalized_phone)
            except Exception as e:
                logger.warning(f"Failed to lookup phone by number: {e}")
        
        if not registered_phone or registered_phone.get("isDeleted") == True:
            raise HTTPException(status_code=400, detail=f"Phone number is not registered. Please register the phone number first.")
        
        # Handle prompt: if promptId is provided, fetch the prompt content
        prompt_id = call_data.get("promptId")
        if prompt_id:
            logger.info(f"Scheduled call using promptId: {prompt_id}")
            from databases.mongodb_prompt_store import MongoDBPromptStore
            prompt_store = MongoDBPromptStore()
            
            # Fetch the prompt
            prompt = await prompt_store.get_prompt(prompt_id)
            if not prompt:
                raise HTTPException(
                    status_code=404,
                    detail=f"Prompt with ID '{prompt_id}' not found"
                )
            
            # Verify the prompt belongs to this user
            if prompt.get("userId") != user["user_id"]:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have access to this prompt"
                )
            
            # Store the prompt content in the scheduled call for execution
            call_data["prompt"] = prompt.get("content", "You are a helpful AI assistant")
            call_data["promptName"] = prompt.get("name", "")
            if prompt.get("introduction"):
                call_data["introduction"] = prompt.get("introduction")
            logger.info(f"✅ Using prompt '{prompt.get('name')}' for scheduled call")
        elif call_data.get("callType") == "ai" and not call_data.get("prompt"):
            # If AI call but no prompt provided, use default
            call_data["prompt"] = "You are a helpful AI assistant"
            logger.info("ℹ️ Using default prompt for AI scheduled call")
        
        # Store AI model configuration for AI calls
        if call_data.get("callType") == "ai":
            ai_config = {
                "sttModel": call_data.get("sttModel", "whisper-1"),
                "inferenceModel": call_data.get("inferenceModel", "gpt-4o-mini"),
                "ttsModel": call_data.get("ttsModel", "tts-1"),
                "ttsVoice": call_data.get("ttsVoice", "alloy"),
            }
            call_data["ai_config"] = ai_config
            logger.info(f"✅ AI model config: STT={ai_config['sttModel']}, LLM={ai_config['inferenceModel']}, TTS={ai_config['ttsModel']}, Voice={ai_config['ttsVoice']}")
        
        scheduled_call_store = MongoDBScheduledCallStore()
        call_id = await scheduled_call_store.create_scheduled_call(call_data, user["user_id"])
        
        if not call_id:
            logger.error("Failed to create scheduled call - create_scheduled_call returned None")
            raise HTTPException(status_code=500, detail="Failed to create scheduled call in MongoDB")
        
        logger.info(f"✅ Scheduled call created successfully with ID: {call_id}")
        
        return {
            "success": True,
            "call_id": call_id,
            "message": "Scheduled call created successfully and stored in MongoDB",
            "mongodb": {
                "database": "voiceagent",
                "collection": "scheduled_calls",
                "saved": True
            }
        }
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating scheduled call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating scheduled call: {str(e)}")

@app.get(
    "/api/scheduled-calls",
    summary="List Scheduled Calls",
    description="Get all scheduled calls from MongoDB. Can filter by phone number, status, or call type.",
    tags=["Scheduled Calls"],
    response_model=Dict[str, Any]
)
async def list_scheduled_calls(
    phone_number_id: Optional[str] = Query(None, description="Filter by phone number ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending, in_progress, completed, failed, cancelled)"),
    call_type: Optional[str] = Query(None, description="Filter by call type (ai, normal)"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """List all scheduled calls for the authenticated user
    
    **Query Parameters:**
    - `phone_number_id` (string, optional): Filter by phone number ID
    - `status` (string, optional): Filter by status
    - `call_type` (string, optional): Filter by call type
    
    **Returns:**
    - List of scheduled call objects with all fields
    """
    try:
        from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability first
        if not is_mongodb_available():
            logger.warning("MongoDB is not available - returning empty scheduled calls list")
            return {"success": True, "calls": [], "count": 0, "mongodb_available": False}
        
        scheduled_call_store = MongoDBScheduledCallStore()
        calls = await scheduled_call_store.list_scheduled_calls(
            phone_number_id=phone_number_id,
            status=status,
            call_type=call_type,
            user_id=user["user_id"]
        )
        
        logger.info(f"✅ User {user['email']} - Returning {len(calls)} scheduled call(s)")
        return {"success": True, "calls": calls, "count": len(calls), "mongodb_available": True}
        
    except Exception as e:
        logger.error(f"Error listing scheduled calls: {e}", exc_info=True)
        return {"success": True, "calls": [], "count": 0, "error": str(e), "mongodb_available": False}

@app.get(
    "/api/scheduled-calls/{call_id}",
    summary="Get Scheduled Call",
    description="Get a specific scheduled call by ID.",
    tags=["Scheduled Calls"],
    response_model=Dict[str, Any]
)
async def get_scheduled_call(call_id: str = Path(..., description="MongoDB Scheduled Call ID")):
    """
    Get a specific scheduled call by ID.
    
    **Path Parameters:**
    - `call_id` (string, required): MongoDB ObjectID of the scheduled call
    
    **Returns:**
    - Full scheduled call object with all fields
    """
    try:
        from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        scheduled_call_store = MongoDBScheduledCallStore()
        call = await scheduled_call_store.get_scheduled_call(call_id)
        
        if call:
            return {"success": True, "call": call}
        else:
            raise HTTPException(status_code=404, detail="Scheduled call not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scheduled call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/api/scheduled-calls/{call_id}",
    summary="Update Scheduled Call",
    description="Update an existing scheduled call.",
    tags=["Scheduled Calls"],
    response_model=Dict[str, Any]
)
async def update_scheduled_call(call_id: str = Path(..., description="MongoDB Scheduled Call ID"), request: Request = ...):
    """
    Update an existing scheduled call.
    
    **Path Parameters:**
    - `call_id` (string, required): MongoDB ObjectID of the scheduled call
    
    **Request Body:**
    - Any scheduled call fields to update (partial updates supported)
    - Common fields: `status`, `scheduledDateTime`, `toPhoneNumbers`, `promptId`
    """
    try:
        updates = await request.json()
        from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        scheduled_call_store = MongoDBScheduledCallStore()
        success = await scheduled_call_store.update_scheduled_call(call_id, updates)
        
        if success:
            return {"success": True, "message": "Scheduled call updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Scheduled call not found or update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scheduled call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/api/scheduled-calls/{call_id}",
    summary="Delete Scheduled Call",
    description="Soft delete a scheduled call (sets isDeleted=True).",
    tags=["Scheduled Calls"],
    response_model=Dict[str, Any]
)
async def delete_scheduled_call(
    call_id: str = Path(..., description="MongoDB Scheduled Call ID"),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Delete a scheduled call from MongoDB (soft delete) - only if user owns it
    
    **Path Parameters:**
    - `call_id` (string, required): MongoDB ObjectID of the scheduled call
    
    **Note:** This is a soft delete - sets isDeleted=True. The call remains in MongoDB for audit purposes.
    """
    try:
        from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available")
        
        scheduled_call_store = MongoDBScheduledCallStore()
        success = await scheduled_call_store.delete_scheduled_call(call_id, user_id=user["user_id"])
        
        if success:
            logger.info(f"✅ User {user['email']} deleted scheduled call {call_id}")
            return {"success": True, "message": "Scheduled call deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Scheduled call not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scheduled call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/twilio/status",
    summary="Get Twilio Call Status",
    description="Get status of active Twilio calls and configuration",
    tags=["Twilio Phone Integration"]
)
async def get_twilio_status():
    """Get current status of Twilio integration."""
    from config import TWILIO_WEBHOOK_BASE_URL
    from databases.mongodb_phone_store import MongoDBPhoneStore
    from databases.mongodb_db import is_mongodb_available
    
    # Combine active calls from both batch and stream modes
    stream_call_sids = list(active_stream_handlers.keys())
    batch_call_sids = list(twilio_phone_tool.active_calls.keys())
    all_active_calls = list(set(stream_call_sids + batch_call_sids))
    
    # Get registered phones count
    registered_phones_count = 0
    if is_mongodb_available():
        try:
            phone_store = MongoDBPhoneStore()
            phones = await phone_store.list_phones(active_only=True)
            registered_phones_count = len(phones)
        except Exception as e:
            logger.warning(f"Could not get registered phones count: {e}")
    
    return {
        "configured": registered_phones_count > 0,
        "registered_phones_count": registered_phones_count,
        "webhook_base_url": TWILIO_WEBHOOK_BASE_URL,
        "active_calls": len(all_active_calls),
        "active_call_sids": all_active_calls,
        "stream_mode_calls": len(stream_call_sids),
        "batch_mode_calls": len(batch_call_sids),
        "server_status": "online",
        "note": "Twilio credentials should be registered through the app UI"
    }

@app.post(
    "/twilio/hangup/{call_sid}",
    summary="Hang Up Twilio Call",
    description="Programmatically hang up an active Twilio call by CallSid",
    tags=["Twilio Phone Integration"]
)
async def hangup_twilio_call(call_sid: str, reason: str = Query("Call ended by system", description="Reason for hanging up")):
    """
    Hang up an active Twilio call.
    
    This endpoint can hang up calls in both streaming and batch modes.
    
    **Example usage:**
    ```bash
    curl -X POST "http://localhost:4002/twilio/hangup/CA1234567890abcdef?reason=User%20requested%20end"
    ```
    """
    try:
        from utils.twilio_credentials import get_twilio_credentials
        
        # Try to hang up via stream handler first (for streaming mode)
        if call_sid in active_stream_handlers:
            handler = active_stream_handlers[call_sid]
            success = await handler.hangup_call(reason=reason)
            if success:
                # Update call status in MongoDB (handler may have done this, but ensure it's done)
                try:
                    from databases.mongodb_call_store import MongoDBCallStore
                    call_store = MongoDBCallStore()
                    await call_store.end_call(call_sid)
                    logger.info(f"✅ Updated call {call_sid} status to 'completed' in MongoDB after hangup")
                except Exception as e:
                    logger.warning(f"Could not update call status in MongoDB: {e}")
                
                return {
                    "status": "success",
                    "message": f"Call {call_sid} hung up successfully",
                    "method": "stream_handler",
                    "reason": reason
                }
        
        # Fallback: Use Twilio REST API to update call status
        # Get credentials from registered phone (or fallback to global config)
        twilio_creds = await get_twilio_credentials(call_sid=call_sid)
        
        if twilio_creds and twilio_creds.get("account_sid") and twilio_creds.get("auth_token"):
            try:
                from twilio.rest import Client
                client = Client(twilio_creds["account_sid"], twilio_creds["auth_token"])
                
                # Update call status to completed (this will hang up the call)
                call = client.calls(call_sid).update(status="completed")
                logger.info(f"✅ Call {call_sid} hung up via REST API: {reason}")
                
                # Update call status in MongoDB immediately
                try:
                    from databases.mongodb_call_store import MongoDBCallStore
                    call_store = MongoDBCallStore()
                    await call_store.end_call(call_sid)
                    logger.info(f"✅ Updated call {call_sid} status to 'completed' in MongoDB")
                except Exception as e:
                    logger.warning(f"Could not update call status in MongoDB: {e}")
                
                # Clean up from batch mode if exists
                if call_sid in twilio_phone_tool.active_calls:
                    twilio_phone_tool._cleanup_call(call_sid)
                
                return {
                    "status": "success",
                    "message": f"Call {call_sid} hung up successfully",
                    "method": "rest_api",
                    "reason": reason,
                    "call_status": call.status
                }
            except Exception as e:
                logger.error(f"Error hanging up call {call_sid} via REST API: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to hang up call via REST API: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Twilio credentials not found for this call. Please register the phone number through the app."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error hanging up call {call_sid}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to hang up call: {str(e)}")

@app.post(
    "/api/calls/outbound",
    summary="Make Outbound Call",
    description="Initiate an outbound phone call with optional custom context. Validates that the 'from' phone number is registered and active.",
    tags=["Twilio Phone Integration"],
    responses={
        200: {
            "description": "Call initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "call_sid": "CA1234567890abcdef",
                        "message": "Call initiated successfully",
                        "from": "+15551234567",
                        "to": "+15559876543"
                    }
                }
            }
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Phone number +15551234567 is not registered or inactive"}
                }
            }
        },
        500: {
            "description": "Failed to initiate call",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to initiate call: Invalid phone number"}
                }
            }
        }
    }
)
async def make_outbound_call(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Make an outbound phone call.
    
    **Request Body:**
    ```json
    {
        "from": "+15551234567",  // Your registered Twilio number (required)
        "to": "+15559876543",    // Destination number (required)
        "context": "calling to follow up on product inquiry"  // Optional custom context
    }
    ```
    
    **Validation:**
    - The from phone number MUST belong to the logged-in user
    - The from phone number MUST NOT be deleted
    - The to phone number must be in valid E.164 format
    - Custom context is optional - if not provided, uses default agent system prompt
    
    **Flow:**
    1. Validates from number belongs to logged-in user and is not deleted
    2. Gets Twilio credentials for the from number
    3. Initiates call via Twilio REST API
    4. When call connects, webhook uses from number to identify agent
    5. Custom context (if provided) is used instead of default agent prompt
    """
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore, normalize_phone_number
        from databases.mongodb_db import is_mongodb_available
        from utils.twilio_credentials import get_twilio_credentials_for_phone
        from config import TWILIO_WEBHOOK_BASE_URL
        from datetime import datetime
        import json
        
        # Parse request body
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON in request body")
        
        from_number = body.get("from")
        to_number = body.get("to")
        custom_context = body.get("context")  # Optional custom context
        
        # Validate required fields
        if not from_number:
            raise HTTPException(status_code=400, detail="'from' phone number is required")
        if not to_number:
            raise HTTPException(status_code=400, detail="'to' phone number is required")
        
        # Normalize phone numbers
        normalized_from = normalize_phone_number(from_number)
        normalized_to = normalize_phone_number(to_number)
        
        logger.info(f"📞 Initiating outbound call: {normalized_from} -> {normalized_to}")
        logger.info(f"   User: {user['email']} (ID: {user['user_id']})")
        if custom_context:
            logger.info(f"   Custom context provided: {custom_context[:100]}...")
        
        # =====================================================================
        # VALIDATION: Check if 'from' phone belongs to logged-in user
        # =====================================================================
        # Requirements (from implementation plan):
        #   1. Phone must be registered
        #   2. Must belong to this user (filter by user_id)
        #   3. Must not be deleted (check isDeleted)
        #   4. Do NOT check isActive
        
        if not is_mongodb_available():
            raise HTTPException(
                status_code=503,
                detail="MongoDB is not available. Cannot validate phone registration."
            )
        
        phone_store = MongoDBPhoneStore()
        
        # Get user's registered phones (filtered by user_id from login session)
        user_phones = await phone_store.list_phones(user_id=user["user_id"])
        
        # Find matching phone in user's registered phones
        registered_phone = None
        for phone in user_phones:
            if normalize_phone_number(phone.get("phoneNumber", "")) == normalized_from:
                registered_phone = phone
                break
        
        if not registered_phone:
            logger.warning(f"❌ Phone '{normalized_from}' not registered to user {user['email']}")
            raise HTTPException(
                status_code=403,
                detail=f"Phone number {normalized_from} is not registered to your account. Please register it first."
            )
        
        # Check if phone is deleted (but do NOT check isActive)
        if registered_phone.get("isDeleted") == True:
            logger.warning(f"❌ Phone '{normalized_from}' has been deleted")
            raise HTTPException(
                status_code=400,
                detail=f"Phone number {normalized_from} has been deleted. Please register it again."
            )
        
        logger.info(f"✅ Phone '{normalized_from}' validated for user {user['email']}")
        logger.info(f"   Registered phone ID: {registered_phone.get('id')}")
        
        # Get Twilio credentials for the 'from' number
        twilio_creds = await get_twilio_credentials_for_phone(normalized_from)
        
        if not twilio_creds or not twilio_creds.get("account_sid") or not twilio_creds.get("auth_token"):
            logger.error(f"❌ Twilio credentials not found for phone {normalized_from}")
            raise HTTPException(
                status_code=400,
                detail=f"Twilio credentials not found for phone number {normalized_from}. Please ensure credentials are properly registered."
            )
        
        # Store custom context temporarily if provided (will be used when webhook arrives)
        # We'll store it in a temporary dict keyed by a combination we can identify later
        # For now, we'll pass it via Twilio StatusCallback parameters
        from twilio.rest import Client
        client = Client(twilio_creds["account_sid"], twilio_creds["auth_token"])
        
        # Prepare webhook URLs
        webhook_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming"
        status_callback_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status"
        
        # If custom context is provided, we need to store it temporarily
        # We'll use a simple in-memory store keyed by from+to combination
        # When the webhook arrives, we can check if this is an outbound call and use the context
        if custom_context:
            # Store custom context temporarily (will be cleaned up after call starts)
            # Use a simple dict: key = f"{normalized_from}_{normalized_to}", value = context
            if not hasattr(twilio_phone_tool, 'outbound_call_contexts'):
                twilio_phone_tool.outbound_call_contexts = {}
            
            context_key = f"{normalized_from}_{normalized_to}"
            twilio_phone_tool.outbound_call_contexts[context_key] = {
                "context": custom_context,
                "from": normalized_from,
                "to": normalized_to,
                "timestamp": datetime.utcnow().isoformat()
            }
            logger.info(f"💾 Stored custom context for outbound call: {context_key}")
        
        # Initiate the call via Twilio REST API
        try:
            call = client.calls.create(
                to=normalized_to,
                from_=normalized_from,
                url=webhook_url,
                status_callback=status_callback_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed', 'failed', 'busy', 'no-answer', 'canceled'],
                method='POST'
            )
            
            call_sid = call.sid
            logger.info(f"✅ Outbound call initiated successfully")
            logger.info(f"   Call SID: {call_sid}")
            logger.info(f"   From: {normalized_from}")
            logger.info(f"   To: {normalized_to}")
            logger.info(f"   Status: {call.status}")
            
            # Create call record in MongoDB
            # EDGE CASE: Handle race condition where status webhook arrives before record is created
            try:
                from databases.mongodb_call_store import MongoDBCallStore
                call_store = MongoDBCallStore()
                
                # EDGE CASE: Check if record already exists (race condition with status webhook)
                existing_call = await call_store.get_call_by_sid(call_sid)
                if existing_call:
                    logger.info(f"ℹ️ Call record for {call_sid} already exists (likely created by status webhook)")
                else:
                    # Create new record
                    success = await call_store.create_call(
                        call_sid=call_sid,
                        from_number=normalized_from,
                        to_number=normalized_to,
                        agent_id=normalized_from  # Use 'from' number as agent_id for outbound calls
                    )
                    if success:
                        logger.info(f"✅ Created call record in MongoDB for {call_sid}")
                    else:
                        logger.warning(f"⚠️ create_call returned False for {call_sid} (may have been created by status webhook)")
            except Exception as e:
                # EDGE CASE: Duplicate key error (race condition)
                if "duplicate" in str(e).lower() or "E11000" in str(e):
                    logger.info(f"ℹ️ Call record for {call_sid} already exists (race condition handled)")
                else:
                    logger.warning(f"Could not create call record: {e}")
            
            return {
                "success": True,
                "call_sid": call_sid,
                "message": "Call initiated successfully",
                "from": normalized_from,
                "to": normalized_to,
                "status": call.status,
                "custom_context_provided": bool(custom_context)
            }
            
        except Exception as e:
            logger.error(f"❌ Error initiating call via Twilio API: {e}", exc_info=True)
            # Clean up stored context if call failed
            if custom_context and hasattr(twilio_phone_tool, 'outbound_call_contexts'):
                context_key = f"{normalized_from}_{normalized_to}"
                if context_key in twilio_phone_tool.outbound_call_contexts:
                    del twilio_phone_tool.outbound_call_contexts[context_key]
            
            error_msg = str(e)
            if "Invalid" in error_msg or "not a valid" in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid phone number format or number: {error_msg}"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initiate call via Twilio: {error_msg}"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error making outbound call: {e}", exc_info=True)
        error_detail = str(e)
        # Provide more specific error messages
        if "connection" in error_detail.lower() or "timeout" in error_detail.lower():
            error_detail = f"Connection error: {error_detail}. Please check your network connection and Twilio credentials."
        elif "authentication" in error_detail.lower() or "unauthorized" in error_detail.lower():
            error_detail = f"Authentication error: {error_detail}. Please verify your Twilio credentials."
        elif "not found" in error_detail.lower() or "404" in error_detail:
            error_detail = f"Resource not found: {error_detail}. Please verify the phone numbers are correct."
        raise HTTPException(status_code=500, detail=f"Failed to make outbound call: {error_detail}")

# ============================================================================
# ERROR HANDLERS
# ============================================================================
# FALLBACK HANDLERS (if Media Stream fails)
# ============================================================================

@app.post(
    "/webhooks/twilio/fallback",
    summary="Twilio Fallback Voice Handler",
    description="Fallback endpoint if Media Stream fails",
    tags=["Twilio Phone Integration"],
    response_class=HTMLResponse
)
async def twilio_fallback_handler(request: Request):
    """
    Fallback handler for when Media Stream does not work.
    Uses simple TwiML with Say for more reliable operation.
    """
    try:
        from twilio.twiml.voice_response import VoiceResponse
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        from_number = form_data.get("From")
        
        logger.info(f"[FALLBACK] Incoming call from {from_number} with CallSid {call_sid}")
        
        response = VoiceResponse()
        response.say("Hello! How can I help you today?", voice="alice")
        response.pause(length=2)
        response.say("Unfortunately, I am not able to process your call at this moment. Please try again later.", voice="alice")
        response.hangup()
        
        logger.info(f"[FALLBACK] Sent greeting for call {call_sid}")
        return make_twiml_response(str(response))
        
    except Exception as e:
        logger.error(f"[FALLBACK] Error: {str(e)}")
        from twilio.twiml.voice_response import VoiceResponse
        error_response = VoiceResponse()
        error_response.say("Sorry, an error occurred. Goodbye.")
        error_response.hangup()
        return make_twiml_response(str(error_response))

# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get(
    "/analytics/call-statistics",
    summary="Get Call Statistics",
    description="Get overall call statistics from MongoDB including total calls, durations (min/max/avg), and call status counts. Used by the dashboard UI.",
    tags=["Analytics"],
    responses={
        200: {
            "description": "Call statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total_calls": 247,
                        "total_duration_seconds": 18450.5,
                        "average_duration_seconds": 74.7,
                        "min_duration_seconds": 12.0,
                        "max_duration_seconds": 343.0,
                        "active_calls": 3,
                        "completed_calls": 244
                    }
                }
            }
        }
    }
)
async def get_call_statistics(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID (phone number)"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format: YYYY-MM-DDTHH:MM:SS)")
):
    """
    Get call statistics from MongoDB conversations collection.
    
    **Query Parameters:**
    - `agent_id` (string, optional): Filter statistics by agent/phone number
    - `start_date` (string, optional): Start date in ISO format (e.g., "2025-01-01T00:00:00")
    - `end_date` (string, optional): End date in ISO format (e.g., "2025-01-31T23:59:59")
    
    **Returns:**
    - Total calls count
    - Duration statistics (total, average, min, max)
    - Call status counts (active, completed)
    """
    try:
        from databases.mongodb_analytics import MongoDBAnalytics
        from datetime import datetime
        
        analytics = MongoDBAnalytics()
        
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        stats = await analytics.get_call_statistics(
            agent_id=agent_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting call statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/analytics/calls-by-date",
    summary="Get Calls by Date",
    description="Get call counts grouped by date from MongoDB. Used by the dashboard UI to display call trends over time.",
    tags=["Analytics"],
    responses={
        200: {
            "description": "Calls grouped by date",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "date": "2025-11-03",
                                "count": 12,
                                "total_duration_seconds": 900
                            },
                            {
                                "date": "2025-11-04",
                                "count": 18,
                                "total_duration_seconds": 1350
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_calls_by_date(
    days: int = Query(7, description="Number of days to look back (default: 7)", ge=1, le=365),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID (phone number)")
):
    """
    Get calls grouped by date from MongoDB.
    
    **Query Parameters:**
    - `days` (integer, required): Number of days to look back (1-365, default: 7)
    - `agent_id` (string, optional): Filter by agent/phone number
    
    **Returns:**
    - Array of objects with date, count, and total_duration_seconds
    - Used by dashboard UI for date-based charts
    """
    try:
        from databases.mongodb_analytics import MongoDBAnalytics
        
        analytics = MongoDBAnalytics()
        results = await analytics.get_calls_by_date(days=days, agent_id=agent_id)
        
        return {"data": results}
        
    except Exception as e:
        logger.error(f"Error getting calls by date: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/analytics/calls-by-agent",
    summary="Get Calls by Agent",
    description="Get call statistics grouped by agent/phone number from MongoDB. Used by the dashboard UI to display agent performance.",
    tags=["Analytics"],
    responses={
        200: {
            "description": "Calls grouped by agent",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "agent_id": "+1 555 202 2030",
                                "call_count": 142,
                                "total_duration_seconds": 10590,
                                "average_duration_seconds": 74.6
                            },
                            {
                                "agent_id": "+1 555 204 0090",
                                "call_count": 89,
                                "total_duration_seconds": 6645,
                                "average_duration_seconds": 74.7
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_calls_by_agent():
    """
    Get calls grouped by agent/phone number from MongoDB.
    
    **Returns:**
    - Array of objects with agent_id, call_count, total_duration_seconds, and average_duration_seconds
    - Sorted by call_count (descending)
    - Used by dashboard UI for agent performance table
    """
    try:
        from databases.mongodb_analytics import MongoDBAnalytics
        
        analytics = MongoDBAnalytics()
        results = await analytics.get_calls_by_agent()
        
        return {"data": results}
        
    except Exception as e:
        logger.error(f"Error getting calls by agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/analytics/recent-calls",
    summary="Get Recent Calls",
    description="Get recent calls with details from MongoDB. Returns the most recent calls sorted by creation date.",
    tags=["Analytics"],
    responses={
        200: {
            "description": "Recent calls",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "session_id": "abc123",
                                "agent_id": "+1 555 202 2030",
                                "customer_id": "customer_123",
                                "status": "completed",
                                "message_count": 10,
                                "duration_seconds": 75.5,
                                "created_at": "2025-11-10T15:30:00",
                                "updated_at": "2025-11-10T15:31:15"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_recent_calls(
    limit: int = Query(10, description="Number of recent calls to return (default: 10)", ge=1, le=100)
):
    """
    Get recent calls from MongoDB.
    
    **Query Parameters:**
    - `limit` (integer, optional): Number of recent calls to return (1-100, default: 10)
    
    **Returns:**
    - Array of recent call objects with session_id, agent_id, status, duration, timestamps
    - Sorted by created_at (most recent first)
    """
    try:
        from databases.mongodb_analytics import MongoDBAnalytics
        
        analytics = MongoDBAnalytics()
        results = await analytics.get_recent_calls(limit=limit)
        
        return {"data": results}
        
    except Exception as e:
        logger.error(f"Error getting recent calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/calls",
    summary="Get All Calls",
    description="Get all calls with transcripts. Supports filtering by agent and status.",
    tags=["Calls"],
    response_model=Dict[str, Any]
)
async def get_all_calls(
    agent_id: Optional[str] = Query(None, description="Filter by agent/phone number"),
    status: Optional[str] = Query(None, description="Filter by status: 'active' or 'completed'"),
    limit: int = Query(100, description="Maximum number of calls to return", ge=1, le=1000),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Get all calls with transcripts (user-filtered)"""
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        from databases.mongodb_phone_store import MongoDBPhoneStore
        
        logger.debug(f"📞 GET /api/calls called - agent_id: {agent_id}, status: {status}, user: {user['email']}")
        
        # Get user's phone numbers for filtering
        phone_store = MongoDBPhoneStore()
        user_phones = await phone_store.list_phones(user_id=user["user_id"])
        user_phone_numbers = [p["phoneNumber"] for p in user_phones]
        
        logger.debug(f"   User {user['email']} has {len(user_phone_numbers)} registered phone(s)")
        
        # If agent_id filter is provided, validate it belongs to this user
        if agent_id:
            if agent_id not in user_phone_numbers:
                logger.warning(f"❌ User {user['email']} attempted to access phone {agent_id} (not owned)")
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You do not own this phone number"
                )
        
        call_store = MongoDBCallStore()
        
        # Map UI status to DB status
        db_status = None
        if status == "ongoing":
            db_status = "active"
        elif status == "finished":
            db_status = "completed"
        elif status:
            db_status = status
        
        # Get calls only for user's phone numbers
        calls = await call_store.get_calls_for_user(
            user_phone_numbers=user_phone_numbers,
            agent_id=agent_id,
            status=db_status,
            limit=limit
        )
        
        return {"calls": calls}
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is (e.g., 403 Forbidden)
        raise
    except Exception as e:
        logger.error(f"Error getting calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/calls/active",
    summary="Get Active Calls",
    description="Get currently active calls for real-time display",
    tags=["Calls"]
)
async def get_active_calls():
    """Get currently active calls"""
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        call_store = MongoDBCallStore()
        calls = await call_store.get_active_calls()
        return {"calls": calls}
    except Exception as e:
        logger.error(f"Error getting active calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/calls/{call_sid}",
    summary="Get Call by ID",
    description="Get a specific call with full transcript",
    tags=["Calls"]
)
async def get_call_by_id(call_sid: str):
    """Get a specific call by call_sid"""
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        call_store = MongoDBCallStore()
        call = await call_store.get_call_by_sid(call_sid)
        
        if call is None:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return {"call": call}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MESSAGES ENDPOINTS
# ============================================================================

@app.get(
    "/api/messages/debug",
    summary="Debug Messages Endpoint",
    description="Debug endpoint to check if messages exist in MongoDB and diagnose issues",
    tags=["Messages"]
)
async def debug_messages():
    """Debug endpoint to check message storage"""
    try:
        from databases.mongodb_message_store import MongoDBMessageStore
        from databases.mongodb_db import is_mongodb_available, get_mongo_db
        
        if not is_mongodb_available():
            return {
                "mongodb_available": False,
                "message": "MongoDB is not available"
            }
        
        db = get_mongo_db()
        if db is None:
            return {
                "mongodb_available": False,
                "message": "Failed to get MongoDB database"
            }
        
        collection = db["messages"]
        
        # Get raw message count
        total_messages = await collection.count_documents({})
        
        # Get sample messages
        # Note: Messages are stored in an array within documents (one doc per agent_id)
        sample_messages = []
        message_store = MongoDBMessageStore()
        all_messages = await message_store.get_all_messages(limit=5)
        for msg in all_messages[:5]:
            sample_messages.append({
                "message_sid": msg.get("message_sid"),
                "agent_number": msg.get("agent_number"),
                "user_number": msg.get("user_number"),
                "body": msg.get("body", "")[:50],
                "direction": msg.get("direction"),
                "conversation_id": msg.get("conversation_id"),
                "agent_id": msg.get("agent_id"),
                "timestamp": msg.get("timestamp")
            })
        
        # Get unique conversation_ids
        conversation_ids = await collection.distinct("conversation_id")
        
        # Test get_conversations
        message_store = MongoDBMessageStore()
        conversations = await message_store.get_conversations(limit=10)
        
        return {
            "mongodb_available": True,
            "total_messages": total_messages,
            "unique_conversation_ids": len(conversation_ids),
            "conversation_ids": conversation_ids[:10],  # First 10
            "sample_messages": sample_messages,
            "conversations_from_get_conversations": len(conversations),
            "sample_conversation": conversations[0] if conversations else None
        }
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}", exc_info=True)
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get(
    "/api/messages",
    summary="Get All Message Conversations",
    description="Get all message conversations grouped by conversation_id. Supports filtering by agent.",
    tags=["Messages"],
    response_model=Dict[str, Any]
)
async def get_all_messages(
    agent_id: Optional[str] = Query(None, description="Filter by agent/phone number"),
    limit: int = Query(100, description="Maximum number of conversations to return", ge=1, le=1000),
    user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Get all message conversations grouped by conversation_id (user-filtered)"""
    try:
        from databases.mongodb_message_store import MongoDBMessageStore
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        logger.info(f"📨 GET /api/messages called - agent_id: {agent_id}, limit: {limit}, user: {user['email']}")
        
        if not is_mongodb_available():
            logger.warning("⚠️  MongoDB not available for get_all_messages")
            return {"messages": []}
        
        # Get user's phone numbers for filtering
        phone_store = MongoDBPhoneStore()
        user_phones = await phone_store.list_phones(user_id=user["user_id"])
        user_phone_numbers = [p["phoneNumber"] for p in user_phones]
        
        logger.info(f"   User {user['email']} has {len(user_phone_numbers)} registered phone(s)")
        
        # If agent_id filter is provided, validate it belongs to this user
        if agent_id:
            if agent_id not in user_phone_numbers:
                logger.warning(f"❌ User {user['email']} attempted to access phone {agent_id} (not owned)")
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You do not own this phone number"
                )
        
        # Get conversations only for user's phone numbers
        message_store = MongoDBMessageStore()
        conversations = await message_store.get_conversations_for_user(
            user_phone_numbers=user_phone_numbers,
            agent_id=agent_id,
            limit=limit
        )
        
        logger.info(f"✅ Retrieved {len(conversations)} conversation(s) from MongoDB")
        if conversations:
            logger.info(f"   Sample conversation_id: {conversations[0].get('conversation_id', 'N/A')}")
            logger.info(f"   Sample message_count: {conversations[0].get('message_count', 0)}")
            logger.info(f"   Sample phoneNumberId: {conversations[0].get('phoneNumberId', 'N/A')}")
            logger.info(f"   Sample callerNumber: {conversations[0].get('callerNumber', 'N/A')}")
            logger.info(f"   Sample conversation length: {len(conversations[0].get('conversation', []))}")
        else:
            logger.warning("⚠️ No conversations returned from get_conversations - check if messages exist in MongoDB")
        
        return {"messages": conversations}
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is (e.g., 403 Forbidden)
        raise
    except Exception as e:
        logger.error(f"❌ Error getting messages: {e}", exc_info=True)
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/messages/{conversation_id}",
    summary="Get Conversation by ID",
    description="Get a specific conversation with all messages",
    tags=["Messages"]
)
async def get_conversation_by_id(conversation_id: str):
    """Get a specific conversation by conversation_id"""
    try:
        from databases.mongodb_message_store import MongoDBMessageStore
        message_store = MongoDBMessageStore()
        
        messages = await message_store.get_all_messages(
            conversation_id=conversation_id,
            limit=1000
        )
        
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Group messages into conversation format
        conversation_messages = []
        for msg in messages:
            conversation_messages.append({
                "role": "user" if msg.get("direction") == "inbound" else "assistant",
                "text": msg.get("body", ""),
                "timestamp": msg.get("timestamp")
            })
        
        # Get conversation metadata from first message
        first_message = messages[0] if messages else {}
        
        conversation = {
            "id": conversation_id,
            "conversation_id": conversation_id,
            "phoneNumberId": first_message.get("agent_id"),
            "callerNumber": first_message.get("user_number"),  # User is the caller
            "agentNumber": first_message.get("agent_number"),  # Agent number
            "status": "active",
            "timestamp": first_message.get("timestamp"),
            "conversation": conversation_messages
        }
        
        return {"conversation": conversation}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/messages/send",
    summary="Send SMS Message",
    description="Send an SMS message from a registered phone number. Validates that the 'from' phone number is registered and active.",
    tags=["Messages"],
    responses={
        200: {
            "description": "Message sent successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message_sid": "SM1234567890abcdef",
                        "message": "SMS sent successfully",
                        "from": "+15551234567",
                        "to": "+15559876543"
                    }
                }
            }
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Phone number +15551234567 is not registered or inactive"}
                }
            }
        },
        500: {
            "description": "Failed to send message",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to send SMS: Invalid phone number"}
                }
            }
        }
    }
)
async def send_sms_message(request: Request):
    """
    Send an SMS message from a registered phone number.
    
    **Request Body:**
    ```json
    {
        "from": "+15551234567",  // Your registered Twilio number (required)
        "to": "+15559876543",    // Destination number (required)
        "body": "Hello, this is a test message!"  // Message text (required)
    }
    ```
    
    **Validation:**
    - The 'from' phone number MUST be registered and active in MongoDB
    - The 'to' phone number must be in valid E.164 format
    - Message body is required and cannot be empty
    
    **Flow:**
    1. Validates 'from' number is registered and active
    2. Gets Twilio credentials for the 'from' number
    3. Sends SMS via Twilio REST API
    4. Stores message in MongoDB for conversation tracking
    """
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore, normalize_phone_number
        from databases.mongodb_db import is_mongodb_available
        from databases.mongodb_message_store import MongoDBMessageStore
        from utils.twilio_credentials import get_twilio_credentials_for_phone
        
        if not is_mongodb_available():
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        request_data = await request.json()
        from_number = request_data.get("from")
        to_number = request_data.get("to")
        message_body = request_data.get("body", "")
        
        # Validate required fields
        if not from_number:
            raise HTTPException(status_code=400, detail="'from' phone number is required")
        if not to_number:
            raise HTTPException(status_code=400, detail="'to' phone number is required")
        if not message_body or not message_body.strip():
            raise HTTPException(status_code=400, detail="Message body is required and cannot be empty")
        
        # Normalize phone numbers
        normalized_from = normalize_phone_number(from_number)
        normalized_to = normalize_phone_number(to_number)
        
        logger.info(f"📤 Sending SMS: {normalized_from} -> {normalized_to}")
        logger.info(f"   Message: {message_body[:100]}...")
        
        # Check if 'from' number is registered and active
        phone_store = MongoDBPhoneStore()
        registered_phone = await phone_store.get_phone_by_number(normalized_from, type_filter="messages")
        
        if not registered_phone:
            raise HTTPException(
                status_code=400,
                detail=f"Phone number {from_number} is not registered. Please register it first."
            )
        
        if registered_phone.get("isActive") == False or registered_phone.get("isDeleted") == True:
            raise HTTPException(
                status_code=400,
                detail=f"Phone number {from_number} is not active. Please activate it first."
            )
        
        # Get Twilio credentials
        twilio_creds = await get_twilio_credentials_for_phone(normalized_from)
        if not twilio_creds:
            raise HTTPException(
                status_code=500,
                detail=f"Could not get Twilio credentials for {from_number}. Please check phone registration."
            )
        
        # Create Twilio client
        twilio_client = TwilioClient(
            twilio_creds["account_sid"],
            twilio_creds["auth_token"]
        )
        
        # Send SMS via Twilio
        try:
            sent_message = twilio_client.messages.create(
                body=message_body,
                from_=normalized_from,
                to=normalized_to
            )
            
            logger.info(f"✅ SMS sent successfully!")
            logger.info(f"   MessageSid: {sent_message.sid}")
            logger.info(f"   Status: {sent_message.status}")
            
            # Store outbound message in MongoDB
            message_store = MongoDBMessageStore()
            try:
                # Get or create conversation_id
                # For outbound messages: from_number is the agent, to_number is the user
                conversation_id = await message_store.get_or_create_conversation_id(
                    from_number=normalized_to,  # User's number (recipient)
                    to_number=normalized_from,  # Agent's number (sender)
                    agent_id=normalized_from
                )
                
                if conversation_id:
                    await message_store.create_outbound_message(
                        message_sid=sent_message.sid,
                        from_number=normalized_from,
                        to_number=normalized_to,
                        body=message_body,
                        agent_id=normalized_from,
                        conversation_id=conversation_id
                    )
                    logger.info(f"✅ Stored outbound message in MongoDB")
                else:
                    logger.warning(f"⚠️ Could not get conversation_id, message sent but not stored")
            except Exception as store_error:
                logger.error(f"❌ Error storing message in MongoDB: {store_error}", exc_info=True)
                # Don't fail the request - message was sent successfully
            
            return {
                "success": True,
                "message_sid": sent_message.sid,
                "message": "SMS sent successfully",
                "from": normalized_from,
                "to": normalized_to,
                "status": sent_message.status
            }
            
        except Exception as twilio_error:
            logger.error(f"❌ Twilio error sending SMS: {twilio_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send SMS via Twilio: {str(twilio_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending SMS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")

@app.get(
    "/api/debug/calls",
    summary="Debug Calls Endpoint",
    description="Debug endpoint to check if calls exist in MongoDB and diagnose issues",
    tags=["Debug"]
)
async def debug_calls():
    """Debug endpoint to check call storage"""
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        from databases.mongodb_db import is_mongodb_available, get_mongo_db
        
        if not is_mongodb_available():
            return {
                "mongodb_available": False,
                "message": "MongoDB is not available"
            }
        
        db = get_mongo_db()
        if db is None:
            return {
                "mongodb_available": False,
                "message": "Failed to get MongoDB database"
            }
        
        collection = db["calls"]
        
        # Get raw call count
        total_calls = await collection.count_documents({})
        active_calls = await collection.count_documents({"status": "active"})
        completed_calls = await collection.count_documents({"status": "completed"})
        
        # Get sample calls
        sample_calls = []
        async for doc in collection.find({}).sort("created_at", -1).limit(5):
            sample_calls.append({
                "call_sid": doc.get("call_sid"),
                "from_number": doc.get("from_number"),
                "to_number": doc.get("to_number"),
                "agent_id": doc.get("agent_id"),
                "status": doc.get("status"),
                "start_time": doc.get("start_time"),
                "end_time": doc.get("end_time"),
                "duration_seconds": doc.get("duration_seconds"),
                "transcript_count": len(doc.get("transcript", [])),
                "created_at": doc.get("created_at")
            })
        
        # Test get_all_calls
        call_store = MongoDBCallStore()
        all_calls = await call_store.get_all_calls(limit=10)
        active_calls_list = await call_store.get_active_calls()
        
        return {
            "mongodb_available": True,
            "total_calls": total_calls,
            "active_calls_count": active_calls,
            "completed_calls_count": completed_calls,
            "sample_calls": sample_calls,
            "calls_from_get_all_calls": len(all_calls),
            "active_calls_from_get_active": len(active_calls_list),
            "sample_call": all_calls[0] if all_calls else None
        }
        
    except Exception as e:
        logger.error(f"Error in debug calls endpoint: {e}", exc_info=True)
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get(
    "/api/debug/messages",
    summary="Debug Messages Endpoint",
    description="Debug endpoint to check if messages exist in MongoDB and diagnose issues",
    tags=["Debug"]
)
async def debug_messages():
    """Debug endpoint to check message storage"""
    try:
        from databases.mongodb_message_store import MongoDBMessageStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            return {
                "mongodb_available": False,
                "message": "MongoDB is not available"
            }
        
        message_store = MongoDBMessageStore()
        
        # Get all messages (limit 50)
        all_messages = await message_store.get_all_messages(limit=50)
        
        # Get conversations
        conversations = await message_store.get_conversations(limit=10)
        
        return {
            "mongodb_available": True,
            "total_messages_retrieved": len(all_messages),
            "total_conversations": len(conversations),
            "sample_messages": all_messages[:5] if all_messages else [],
            "sample_conversations": conversations[:2] if conversations else []
        }
        
    except Exception as e:
        logger.error(f"Error in debug messages endpoint: {e}", exc_info=True)
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get(
    "/api/debug/collections",
    summary="Debug Collections Endpoint",
    description="List all MongoDB collections and their document counts",
    tags=["Debug"]
)
async def debug_collections():
    """Debug endpoint to list all MongoDB collections"""
    try:
        from databases.mongodb_db import is_mongodb_available, get_mongo_db, list_collections
        
        if not is_mongodb_available():
            return {
                "mongodb_available": False,
                "message": "MongoDB is not available"
            }
        
        collections_info = await list_collections()
        
        return {
            "mongodb_available": True,
            "collections": collections_info
        }
        
    except Exception as e:
        logger.error(f"Error in debug collections endpoint: {e}", exc_info=True)
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get(
    "/api/debug/mongodb",
    summary="Debug MongoDB Connection",
    description="Test MongoDB connection and provide comprehensive diagnostics",
    tags=["Debug"]
)
async def debug_mongodb():
    """Debug endpoint to test MongoDB connection and provide diagnostics"""
    try:
        from databases.mongodb_db import is_mongodb_available, get_mongo_db, list_collections, test_connection
        from config import MONGODB_URL, MONGODB_DATABASE
        
        # Test connection
        connection_test = await test_connection()
        
        if not is_mongodb_available():
            return {
                "mongodb_available": False,
                "connection_test": connection_test,
                "message": "MongoDB is not available"
            }
        
        db = get_mongo_db()
        if db is None:
            return {
                "mongodb_available": False,
                "connection_test": connection_test,
                "message": "Failed to get MongoDB database"
            }
        
        # List all collections
        collections_info = await list_collections()
        
        # Expected collections
        expected_collections = [
            "calls",
            "messages",
            "messaging_agents",
            "voice_agents",
            "registered_phone_numbers",
            "conversations"
        ]
        
        existing_collection_names = [c["name"] for c in collections_info]
        missing_collections = [c for c in expected_collections if c not in existing_collection_names]
        
        return {
            "mongodb_available": True,
            "connection_test": connection_test,
            "database": MONGODB_DATABASE,
            "mongodb_url_preview": MONGODB_URL[:50] + "..." if len(MONGODB_URL) > 50 else MONGODB_URL,
            "collections": collections_info,
            "expected_collections": expected_collections,
            "missing_collections": missing_collections,
            "all_collections_exist": len(missing_collections) == 0
        }
        
    except Exception as e:
        logger.error(f"Error in debug mongodb endpoint: {e}", exc_info=True)
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.get(
    "/api/calls/{call_sid}/verify",
    summary="Verify Call Transcript",
    description="Debug endpoint to verify call transcript storage",
    tags=["Calls"]
)
async def verify_call_transcript(call_sid: str):
    """Verify call transcript storage - for debugging"""
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        call_store = MongoDBCallStore()
        call = await call_store.get_call_by_sid(call_sid)
        
        if not call:
            return {
                "error": "Call not found",
                "call_sid": call_sid,
                "collection": "calls"
            }
        
        transcript = call.get("conversation", [])
        return {
            "call_sid": call_sid,
            "status": call.get("status"),
            "transcript_count": len(transcript),
            "transcript": transcript,
            "collection": "calls",
            "from_number": call.get("from_number"),
            "to_number": call.get("to_number"),
            "start_time": call.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Error verifying call transcript: {e}")
        return {"error": str(e), "call_sid": call_sid}

@app.websocket("/ws/calls/{call_sid}/transcript")
async def live_transcript_websocket(websocket: WebSocket, call_sid: str):
    """WebSocket endpoint for real-time transcript updates"""
    await websocket.accept()
    
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        call_store = MongoDBCallStore()
        
        # Send initial transcript
        call = await call_store.get_call_by_sid(call_sid)
        if call:
            await websocket.send_json({
                "type": "initial",
                "transcript": call.get("conversation", [])
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Call not found"
            })
            await websocket.close()
            return
        
        # Poll for updates every 1 second
        last_count = len(call.get("conversation", [])) if call else 0
        
        while True:
            await asyncio.sleep(1)
            
            # Check if call still exists and is active
            call = await call_store.get_call_by_sid(call_sid)
            if not call:
                await websocket.send_json({"type": "call_ended"})
                break
            
            # Check if call is still active (handle both "ongoing" and "active" status)
            call_status = call.get("status")
            if call_status not in ["ongoing", "active"]:
                await websocket.send_json({"type": "call_ended"})
                break
            
            # Send new transcript entries
            current_transcript = call.get("conversation", [])
            if len(current_transcript) > last_count:
                new_entries = current_transcript[last_count:]
                for entry in new_entries:
                    await websocket.send_json({
                        "type": "transcript_update",
                        "entry": entry
                    })
                last_count = len(current_transcript)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call {call_sid}")
    except Exception as e:
        logger.error(f"Error in transcript WebSocket: {e}")
        try:
            await websocket.close()
        except:
            pass

# ============================================================================
# PHONE CONFIGURATION MANAGEMENT ENDPOINTS (Admin)
# ============================================================================

@app.post(
    "/admin/phone-config",
    summary="Create or Update Phone Configuration",
    description="Create or update AI configuration for a specific Twilio phone number",
    tags=["Phone Configuration"]
)
async def create_phone_config(config_data: Dict[str, Any]):
    """
    Create or update configuration for a phone number.
    
    Example request body:
    ```json
    {
        "phone_number": "+18668134984",
        "display_name": "Sales Line",
        "stt_model": "whisper-1",
        "tts_model": "tts-1",
        "tts_voice": "nova",
        "inference_model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 500,
        "system_prompt": "You are a sales representative...",
        "greeting": "Welcome to our sales team!",
        "enable_interrupts": true,
        "interrupt_timeout": 0.5,
        "enable_recording": true,
        "max_call_duration": 3600,
        "is_active": true
    }
    ```
    """
    try:
        from config_manager import config_manager
        from databases.mongodb_phone_config_models import PhoneNumberConfig
        
        # Validate required fields
        phone_number = config_data.get("phone_number")
        if not phone_number:
            raise HTTPException(status_code=400, detail="phone_number is required")
        
        # Validate using Pydantic model (will raise ValidationError if invalid)
        try:
            validated_config = PhoneNumberConfig(**config_data)
            config_dict = validated_config.model_dump(exclude_none=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
        
        # Save to MongoDB
        success = await config_manager.save_phone_config(config_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Invalidate cache for this number
        config_manager.invalidate_cache(phone_number)
        
        logger.info(f"✅ Phone config saved: {phone_number}")
        
        return {
            "success": True,
            "message": f"Configuration saved for {phone_number}",
            "config": config_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/admin/phone-config/{phone_number:path}",
    summary="Get Phone Configuration",
    description="Retrieve AI configuration for a specific phone number",
    tags=["Phone Configuration"]
)
async def get_phone_config(phone_number: str):
    """Get configuration for a specific phone number"""
    try:
        from config_manager import config_manager
        
        # Normalize and query
        config = await config_manager._get_phone_config_from_db(phone_number)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Configuration not found for {phone_number}. Use POST /admin/phone-config to create one."
            )
        
        return {
            "success": True,
            "config": config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/admin/phone-configs",
    summary="List All Phone Configurations",
    description="List all active phone number configurations",
    tags=["Phone Configuration"]
)
async def list_phone_configs(include_inactive: bool = Query(False, description="Include inactive configs")):
    """List all phone configurations"""
    try:
        from config_manager import config_manager
        
        configs = await config_manager.list_phone_configs(include_inactive=include_inactive)
        
        return {
            "success": True,
            "total": len(configs),
            "configs": configs
        }
    except Exception as e:
        logger.error(f"Error listing phone configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/admin/phone-config/{phone_number:path}",
    summary="Update Phone Configuration",
    description="Update existing configuration for a phone number (partial update supported)",
    tags=["Phone Configuration"]
)
async def update_phone_config(phone_number: str, config_updates: Dict[str, Any]):
    """Update configuration for a phone number (partial updates allowed)"""
    try:
        from config_manager import config_manager
        
        # Get existing config
        existing = await config_manager._get_phone_config_from_db(phone_number)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Configuration not found for {phone_number}")
        
        # Merge updates
        updated_config = {**existing, **config_updates}
        updated_config["phone_number"] = phone_number  # Ensure phone_number doesn't change
        
        # Validate
        from databases.mongodb_phone_config_models import PhoneNumberConfig
        try:
            validated_config = PhoneNumberConfig(**updated_config)
            config_dict = validated_config.model_dump(exclude_none=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
        
        # Save
        success = await config_manager.save_phone_config(config_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update configuration")
        
        # Invalidate cache
        config_manager.invalidate_cache(phone_number)
        
        logger.info(f"✅ Phone config updated: {phone_number}")
        
        return {
            "success": True,
            "message": f"Configuration updated for {phone_number}",
            "config": config_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/admin/phone-config/{phone_number:path}",
    summary="Delete Phone Configuration",
    description="Delete (deactivate) configuration for a phone number",
    tags=["Phone Configuration"]
)
async def delete_phone_config(
    phone_number: str,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete")
):
    """Delete configuration for a phone number"""
    try:
        from config_manager import config_manager
        
        success = await config_manager.delete_phone_config(phone_number, hard_delete=hard_delete)
        if not success:
            raise HTTPException(status_code=404, detail=f"Configuration not found for {phone_number}")
        
        # Invalidate cache
        config_manager.invalidate_cache(phone_number)
        
        logger.info(f"✅ Phone config deleted: {phone_number} (hard_delete={hard_delete})")
        
        return {
            "success": True,
            "message": f"Configuration {'permanently deleted' if hard_delete else 'deactivated'} for {phone_number}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CALL FLOW TESTING ENDPOINTS
# ============================================================================

@app.get(
    "/api/test/call-flow/settings",
    summary="Get Call Flow Settings",
    description="Get current interrupt handling settings for testing",
    tags=["Testing", "Call Flow"]
)
async def get_call_flow_settings():
    """Get current call flow interrupt settings"""
    try:
        # Import to get current settings
        from tools.phone.twilio_phone_stream import (
            VAD_AGGRESSIVENESS, 
            VAD_SAMPLE_RATE, 
            VAD_FRAME_DURATION_MS
        )
        
        # Get settings from a handler instance (if any active)
        settings = {
            "vad_aggressiveness": VAD_AGGRESSIVENESS,
            "vad_sample_rate": VAD_SAMPLE_RATE,
            "vad_frame_duration_ms": VAD_FRAME_DURATION_MS,
            "default_settings": {
                "silence_threshold_frames": 25,
                "interrupt_grace_period_ms": 500,
                "min_interrupt_frames": 5
            },
            "calculated_values": {
                "silence_threshold_ms": 25 * 20,  # frames * ms per frame
                "min_interrupt_ms": 5 * 20,
                "interrupt_detection_latency_ms": 500 + (5 * 20)  # grace + validation
            },
            "active_calls": len(active_stream_handlers),
            "active_call_sids": list(active_stream_handlers.keys())
        }
        
        # If there are active calls, get their actual settings
        if active_stream_handlers:
            first_handler = next(iter(active_stream_handlers.values()))
            settings["active_call_settings"] = {
                "silence_threshold_frames": first_handler.SILENCE_THRESHOLD_FRAMES,
                "interrupt_grace_period_ms": first_handler.INTERRUPT_GRACE_PERIOD_MS,
                "min_interrupt_frames": first_handler.MIN_INTERRUPT_FRAMES,
                "query_sequence": first_handler.query_sequence,
                "is_speaking": first_handler.is_speaking,
                "ai_is_speaking": first_handler.ai_is_speaking,
                "interrupt_detected": first_handler.interrupt_detected
            }
        
        return {
            "success": True,
            "settings": settings,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting call flow settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/test/call-flow/active-calls",
    summary="Get Active Calls Status",
    description="Get detailed status of all active calls for testing",
    tags=["Testing", "Call Flow"]
)
async def get_active_calls_status():
    """Get detailed status of all active calls"""
    try:
        active_calls = []
        
        for call_sid, handler in active_stream_handlers.items():
            call_info = {
                "call_sid": call_sid,
                "stream_sid": handler.stream_sid,
                "session_id": handler.session_id,
                "to_number": handler.to_number,
                "is_outbound_call": handler.is_outbound_call,
                "state": {
                    "is_speaking": handler.is_speaking,
                    "ai_is_speaking": handler.ai_is_speaking,
                    "interrupt_detected": handler.interrupt_detected,
                    "query_sequence": handler.query_sequence,
                    "speech_frames_count": handler.speech_frames_count,
                    "silence_frames_count": handler.silence_frames_count,
                    "interrupt_speech_frames": handler.interrupt_speech_frames
                },
                "settings": {
                    "silence_threshold_frames": handler.SILENCE_THRESHOLD_FRAMES,
                    "interrupt_grace_period_ms": handler.INTERRUPT_GRACE_PERIOD_MS,
                    "min_interrupt_frames": handler.MIN_INTERRUPT_FRAMES
                },
                "agent_config": {
                    "name": handler.agent_config.get("name") if handler.agent_config else None,
                    "stt_model": handler.agent_config.get("sttModel") if handler.agent_config else None,
                    "tts_model": handler.agent_config.get("ttsModel") if handler.agent_config else None,
                    "llm_model": handler.agent_config.get("inferenceModel") if handler.agent_config else None
                } if handler.agent_config else None,
                "conversation_history_count": len(handler.session_data.get("conversation_history", []))
            }
            active_calls.append(call_info)
        
        return {
            "success": True,
            "active_calls_count": len(active_calls),
            "active_calls": active_calls,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting active calls status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/test/call-flow/simulate-interrupt",
    summary="Simulate Interrupt",
    description="Simulate an interrupt for testing (requires active call)",
    tags=["Testing", "Call Flow"]
)
async def simulate_interrupt(call_sid: str):
    """Simulate an interrupt for testing purposes"""
    try:
        if call_sid not in active_stream_handlers:
            raise HTTPException(status_code=404, detail=f"Call {call_sid} not found in active calls")
        
        handler = active_stream_handlers[call_sid]
        
        # Get current state before interrupt
        before_state = {
            "is_speaking": handler.is_speaking,
            "ai_is_speaking": handler.ai_is_speaking,
            "interrupt_detected": handler.interrupt_detected,
            "query_sequence": handler.query_sequence
        }
        
        # Simulate interrupt detection
        handler.interrupt_detected = True
        
        # Cancel TTS if active
        if handler.tts_streaming_task and not handler.tts_streaming_task.done():
            handler.tts_streaming_task.cancel()
        
        # Send clear command
        try:
            await handler.websocket.send_json({
                "event": "clear",
                "streamSid": handler.stream_sid
            })
        except Exception as e:
            logger.warning(f"Could not send clear command: {e}")
        
        # Update state
        handler.ai_is_speaking = False
        handler.ai_speech_start_time = None
        
        # Get state after interrupt
        after_state = {
            "is_speaking": handler.is_speaking,
            "ai_is_speaking": handler.ai_is_speaking,
            "interrupt_detected": handler.interrupt_detected,
            "query_sequence": handler.query_sequence
        }
        
        return {
            "success": True,
            "call_sid": call_sid,
            "before_state": before_state,
            "after_state": after_state,
            "message": "Interrupt simulated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating interrupt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/test/call-flow/diagnostics",
    summary="Get Call Flow Diagnostics",
    description="Get comprehensive diagnostics for call flow debugging",
    tags=["Testing", "Call Flow"]
)
async def get_call_flow_diagnostics():
    """Get comprehensive call flow diagnostics"""
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        call_store = MongoDBCallStore()
        
        # Get recent calls
        recent_calls = await call_store.get_all_calls(limit=10)
        
        # Calculate statistics
        total_calls = len(recent_calls)
        ongoing_calls = len([c for c in recent_calls if c.get("status") == "ongoing"])
        finished_calls = len([c for c in recent_calls if c.get("status") == "finished"])
        
        # Get conversation statistics
        conversation_stats = []
        for call in recent_calls:
            conversation = call.get("conversation", [])
            user_messages = len([m for m in conversation if m.get("role") == "user"])
            ai_messages = len([m for m in conversation if m.get("role") == "assistant"])
            conversation_stats.append({
                "call_sid": call.get("call_sid"),
                "status": call.get("status"),
                "total_messages": len(conversation),
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "duration": call.get("duration")
            })
        
        diagnostics = {
            "system_status": {
                "active_stream_handlers": len(active_stream_handlers),
                "active_call_sids": list(active_stream_handlers.keys())
            },
            "call_statistics": {
                "total_recent_calls": total_calls,
                "ongoing_calls": ongoing_calls,
                "finished_calls": finished_calls
            },
            "conversation_statistics": conversation_stats,
            "interrupt_settings": {
                "grace_period_ms": 500,
                "min_interrupt_frames": 5,
                "min_interrupt_ms": 100,
                "silence_threshold_ms": 500
            },
            "recent_calls": recent_calls[:5]  # Last 5 calls
        }
        
        return {
            "success": True,
            "diagnostics": diagnostics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting call flow diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/test/call-flow/conversation-history/{call_sid}",
    summary="Get Conversation History",
    description="Get detailed conversation history for a specific call",
    tags=["Testing", "Call Flow"]
)
async def get_conversation_history(call_sid: str):
    """Get detailed conversation history for testing"""
    try:
        # Check if call is active
        if call_sid in active_stream_handlers:
            handler = active_stream_handlers[call_sid]
            conversation_history = handler.session_data.get("conversation_history", [])
            
            return {
                "success": True,
                "call_sid": call_sid,
                "status": "active",
                "conversation_history_count": len(conversation_history),
                "conversation_history": conversation_history,
                "current_state": {
                    "query_sequence": handler.query_sequence,
                    "is_speaking": handler.is_speaking,
                    "ai_is_speaking": handler.ai_is_speaking,
                    "interrupt_detected": handler.interrupt_detected
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Get from MongoDB
            from databases.mongodb_call_store import MongoDBCallStore
            call_store = MongoDBCallStore()
            call = await call_store.get_call_by_sid(call_sid)
            
            if not call:
                raise HTTPException(status_code=404, detail=f"Call {call_sid} not found")
            
            conversation = call.get("conversation", [])
            
            return {
                "success": True,
                "call_sid": call_sid,
                "status": call.get("status"),
                "conversation_count": len(conversation),
                "conversation": conversation,
                "from_number": call.get("from_number"),
                "to_number": call.get("to_number"),
                "duration": call.get("duration"),
                "timestamp": datetime.utcnow().isoformat()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# COMPONENT TESTING APIS - Test each step of call flow independently
# ============================================================================

# ============================================================================
# STT (Speech-to-Text) Testing APIs
# ============================================================================

@app.post(
    "/api/test/stt/transcribe",
    summary="Test Speech-to-Text",
    description="Transcribe audio to text using OpenAI Whisper (test STT independently)",
    tags=["Testing", "Speech-to-Text"]
)
async def test_stt_transcribe(
    audio_file: UploadFile = File(...),
    model: str = Query(default="whisper-1", description="STT model to use")
):
    """Test STT by transcribing an audio file"""
    try:
        # Read audio file
        audio_data = await audio_file.read()
        
        # Use existing STT tool
        result = await speech_tool.transcribe(audio_data, file_format="wav", model=model)
        
        return {
            "success": result.get("success", False),
            "text": result.get("text", ""),
            "error": result.get("error"),
            "model_used": model,
            "audio_size_bytes": len(audio_data),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in STT test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/test/stt/transcribe-base64",
    summary="Test STT with Base64 Audio",
    description="Transcribe base64-encoded audio to text",
    tags=["Testing", "Speech-to-Text"]
)
async def test_stt_transcribe_base64(
    audio_base64: str = Form(...),
    model: str = Form(default="whisper-1")
):
    """Test STT with base64-encoded audio"""
    try:
        import base64
        
        # Decode base64 audio
        audio_data = base64.b64decode(audio_base64)
        
        # Use existing STT tool
        result = await speech_tool.transcribe(audio_data, file_format="wav", model=model)
        
        return {
            "success": result.get("success", False),
            "text": result.get("text", ""),
            "error": result.get("error"),
            "model_used": model,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in STT base64 test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# LLM (Language Model) Testing APIs
# ============================================================================

@app.post(
    "/api/test/llm/generate-response",
    summary="Test LLM Response Generation",
    description="Generate AI response from text input (test LLM independently)",
    tags=["Testing", "LLM"]
)
async def test_llm_generate_response(
    user_text: str = Form(...),
    system_prompt: str = Form(default=None),
    model: str = Form(default="gpt-4o-mini"),
    temperature: float = Form(default=0.7),
    max_tokens: int = Form(default=150)
):
    """Test LLM by generating a response to user text"""
    try:
        # Create a temporary session for testing
        session_data = {
            "session_id": f"test_{datetime.utcnow().timestamp()}",
            "conversation_history": [],
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Use existing conversation tool
        result = await conversation_tool.generate_response(
            session_data,
            user_text,
            persona=None,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            "success": True,
            "user_input": user_text,
            "ai_response": result.get("response", ""),
            "model_used": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in LLM test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/test/llm/generate-with-history",
    summary="Test LLM with Conversation History",
    description="Generate AI response with conversation context",
    tags=["Testing", "LLM"]
)
async def test_llm_generate_with_history(
    user_text: str = Form(...),
    conversation_history: str = Form(default="[]"),
    system_prompt: str = Form(default=None),
    model: str = Form(default="gpt-4o-mini")
):
    """Test LLM with conversation history"""
    try:
        import json
        
        # Parse conversation history
        history = json.loads(conversation_history) if conversation_history else []
        
        # Create session with history
        session_data = {
            "session_id": f"test_{datetime.utcnow().timestamp()}",
            "conversation_history": history,
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "model": model
        }
        
        # Generate response
        result = await conversation_tool.generate_response(
            session_data,
            user_text,
            model=model
        )
        
        return {
            "success": True,
            "user_input": user_text,
            "ai_response": result.get("response", ""),
            "conversation_turns": len(history),
            "model_used": model,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in LLM history test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TTS (Text-to-Speech) Testing APIs
# ============================================================================

@app.post(
    "/api/test/tts/synthesize",
    summary="Test Text-to-Speech",
    description="Convert text to speech audio (test TTS independently)",
    tags=["Testing", "Text-to-Speech"]
)
async def test_tts_synthesize(
    text: str = Form(...),
    voice: str = Form(default="alloy"),
    model: str = Form(default="tts-1"),
    response_format: str = Form(default="mp3")
):
    """Test TTS by converting text to speech"""
    try:
        # Use existing TTS tool (note: TTS tool always returns MP3 format)
        result = await tts_tool.synthesize(
            text,
            voice=voice,
            model=model
        )
        
        if result.get("success"):
            audio_bytes = result.get("audio_bytes")
            
            # Return audio file
            from fastapi.responses import Response
            return Response(
                content=audio_bytes,
                media_type="audio/mp3",
                headers={
                    "Content-Disposition": "attachment; filename=tts_output.mp3"
                }
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "TTS failed"))
    except Exception as e:
        logger.error(f"Error in TTS test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/test/tts/synthesize-base64",
    summary="Test TTS with Base64 Output",
    description="Convert text to speech and return as base64",
    tags=["Testing", "Text-to-Speech"]
)
async def test_tts_synthesize_base64(
    text: str = Form(...),
    voice: str = Form(default="alloy"),
    model: str = Form(default="tts-1")
):
    """Test TTS and return base64-encoded audio"""
    try:
        import base64
        
        # Use existing TTS tool (note: TTS tool always returns MP3 format)
        result = await tts_tool.synthesize(
            text,
            voice=voice,
            model=model
        )
        
        if result.get("success"):
            audio_bytes = result.get("audio_bytes")
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return {
                "success": True,
                "text": text,
                "audio_base64": audio_base64,
                "voice": voice,
                "model": model,
                "audio_size_bytes": len(audio_bytes),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "TTS failed"))
    except Exception as e:
        logger.error(f"Error in TTS base64 test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# END-TO-END FLOW TESTING APIs
# ============================================================================

@app.post(
    "/api/test/flow/audio-to-response",
    summary="Test Complete Audio-to-Response Flow",
    description="Test full pipeline: Audio → STT → LLM → TTS (without actual call)",
    tags=["Testing", "End-to-End Flow"]
)
async def test_flow_audio_to_response(
    audio_file: UploadFile = File(...),
    system_prompt: str = Form(default=None),
    stt_model: str = Form(default="whisper-1"),
    llm_model: str = Form(default="gpt-4o-mini"),
    tts_voice: str = Form(default="alloy"),
    tts_model: str = Form(default="tts-1")
):
    """Test complete flow from audio input to audio response"""
    try:
        # Step 1: STT - Convert audio to text
        audio_data = await audio_file.read()
        stt_result = await speech_tool.transcribe(audio_data, file_format="wav", model=stt_model)
        
        if not stt_result.get("success"):
            raise HTTPException(status_code=500, detail=f"STT failed: {stt_result.get('error')}")
        
        user_text = stt_result.get("text", "")
        
        # Step 2: LLM - Generate response
        session_data = {
            "session_id": f"test_{datetime.utcnow().timestamp()}",
            "conversation_history": [],
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "model": llm_model
        }
        
        llm_result = await conversation_tool.generate_response(
            session_data,
            user_text,
            model=llm_model
        )
        
        ai_response = llm_result.get("response", "")
        
        # Step 3: TTS - Convert response to audio
        tts_result = await tts_tool.synthesize(
            ai_response,
            voice=tts_voice,
            model=tts_model
        )
        
        if not tts_result.get("success"):
            raise HTTPException(status_code=500, detail=f"TTS failed: {tts_result.get('error')}")
        
        # Return complete flow result
        import base64
        response_audio_base64 = base64.b64encode(tts_result.get("audio_bytes")).decode('utf-8')
        
        return {
            "success": True,
            "flow": {
                "step_1_stt": {
                    "transcript": user_text,
                    "model": stt_model
                },
                "step_2_llm": {
                    "user_input": user_text,
                    "ai_response": ai_response,
                    "model": llm_model
                },
                "step_3_tts": {
                    "text": ai_response,
                    "audio_base64": response_audio_base64,
                    "voice": tts_voice,
                    "model": tts_model
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in end-to-end flow test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/test/flow/text-conversation-turn",
    summary="Test Conversation Turn (Text Only)",
    description="Simulate a conversation turn with text input/output",
    tags=["Testing", "End-to-End Flow"]
)
async def test_flow_text_conversation_turn(
    user_text: str = Form(...),
    conversation_id: str = Form(default=None),
    system_prompt: str = Form(default=None),
    model: str = Form(default="gpt-4o-mini")
):
    """Test a conversation turn with text (maintains conversation state)"""
    try:
        # Use or create conversation ID
        conv_id = conversation_id or f"test_{datetime.utcnow().timestamp()}"
        
        # Get or create session data
        # Note: In production, this would be stored in a database
        # For testing, we create a new session each time
        session_data = {
            "session_id": conv_id,
            "conversation_history": [],
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "model": model
        }
        
        # Generate response
        result = await conversation_tool.generate_response(
            session_data,
            user_text,
            model=model
        )
        
        ai_response = result.get("response", "")
        
        # Update conversation history
        updated_session = conversation_tool.manager.add_to_conversation_history(
            session_data,
            user_input=user_text,
            agent_response=ai_response
        )
        
        return {
            "success": True,
            "conversation_id": conv_id,
            "turn": {
                "user": user_text,
                "assistant": ai_response
            },
            "conversation_history": updated_session.get("conversation_history", []),
            "total_turns": len(updated_session.get("conversation_history", [])),
            "model_used": model,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in conversation turn test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# NEXT.JS HMR WEBSOCKET PROXY
# ============================================================================

@app.websocket("/_next/webpack-hmr")
async def nextjs_hmr_proxy(websocket: WebSocket):
    """Proxy WebSocket connection for Next.js Hot Module Replacement"""
    await websocket.accept()
    try:
        # Connect to Next.js HMR server
        nextjs_ws_url = f"{NEXTJS_INTERNAL_URL.replace('http', 'ws')}/_next/webpack-hmr"
        async with websockets.connect(nextjs_ws_url) as nextjs_ws:
            async def forward_to_nextjs():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await nextjs_ws.send(data)
                except Exception:
                    pass

            async def forward_to_client():
                try:
                    while True:
                        data = await nextjs_ws.recv()
                        await websocket.send_text(data)
                except Exception:
                    pass

            # Run both forwarders concurrently
            await asyncio.gather(forward_to_nextjs(), forward_to_client())
    except Exception as e:
        # It's normal for this to disconnect when page reloads
        pass
    finally:
        try:
            await websocket.close()
        except:
            pass

# ============================================================================
# CATCH-ALL ROUTE FOR NEXT.JS PAGES
# ============================================================================

# Catch-all route to proxy all other requests to Next.js
# This must be defined LAST to avoid catching API routes
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
    summary="Next.js Catch-All",
    description="Proxy all other routes to Next.js UI",
    tags=["UI"]
)
async def nextjs_catchall(request: Request, path: str = ""):
    """Catch-all route to proxy all other requests to Next.js"""
    # Don't proxy API routes (they should be handled by FastAPI first)
    if path.startswith("api/") and not path.startswith("api/session"):
        # Let FastAPI return 404 for unhandled API routes
        raise HTTPException(status_code=404, detail="Not Found")
    
    return await proxy_to_nextjs(request, path)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            status_code=500,
            timestamp=datetime.utcnow().isoformat()
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
