from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Path, WebSocket, WebSocketDisconnect
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from typing import Optional, Dict, Any, List
import json
import logging
import asyncio
import os
from datetime import datetime
import httpx

# Import all models from the unified models file
from models import (
    # API schemas
    HealthResponse, RootResponse,
    VoiceInputRequest, VoiceInputResponse, VoiceOutputRequest, VoiceOutputResponse,
    ConversationRequest, ConversationResponse, ConversationStartRequest, ConversationStartResponse,
    VoiceAgentProcessResponse, PersonaSummary,
    ErrorResponse, SuccessResponse,
    PaginationRequest, PaginationResponse
)

from voice_processor import VoiceProcessor
from conversation_manager import ConversationManager, ConversationState
from config import DEBUG, API_HOST, API_PORT
from tools import SpeechToTextTool, TextToSpeechTool, ConversationalResponseTool, TwilioPhoneTool
from realtime_websocket import realtime_agent
from personas import get_persona_config, list_personas

# Streaming specific imports
from tools.phone.twilio_phone_stream import TwilioStreamHandler
from twilio.twiml.voice_response import VoiceResponse as TwilioVoiceResponse


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.info("="*50)

# ============================================================================
# GENERAL ENDPOINTS
# ============================================================================


@app.get(
    "/",
    summary="Root Endpoint",
    description="Landing page with links to all UIs and API documentation",
    tags=["General"],
    response_class=HTMLResponse
)
async def root():
    """Root endpoint with links to all available UIs and documentation"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Voice Agent - Home</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                padding: 40px;
                max-width: 600px;
                width: 100%;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 2rem;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
            }
            .links {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }
            .link {
                display: block;
                padding: 15px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                transition: transform 0.2s;
                font-weight: 500;
            }
            .link:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .link-api {
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }
            .link-docs {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎧 Voice Agent</h1>
            <p class="subtitle">AI-powered voice conversation system</p>
            <div class="links">
                <a href="/saas-dashboard" class="link">🚀 SaaS Dashboard - Voice Agent Management</a>
                <a href="/docs" class="link link-docs">📚 API Documentation (Swagger)</a>
                <a href="/redoc" class="link link-docs">📖 API Documentation (ReDoc)</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API",
    tags=["General"]
)
async def health_check():
    """Health check endpoint"""
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
async def mongodb_health_check():
    """MongoDB health check endpoint - verifies connection and availability"""
    try:
        from databases.mongodb_db import is_mongodb_available, test_connection
        
        is_available = is_mongodb_available()
        connection_status = False
        
        if is_available:
            connection_status = await test_connection()
            if connection_status:
                return {
                    "status": "healthy",
                    "mongodb": {
                        "connected": True,
                        "status": "available",
                        "database": "voiceagent"
                    },
                    "service": "voice-agent-api",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "mongodb": {
                        "connected": False,
                        "status": "connection_failed"
                    },
                    "service": "voice-agent-api",
                    "timestamp": datetime.utcnow().isoformat()
                }
        else:
            return {
                "status": "degraded",
                "mongodb": {
                    "connected": False,
                    "status": "not_initialized"
                },
                "service": "voice-agent-api",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        return {
            "status": "unhealthy",
            "mongodb": {
                "connected": False,
                "status": "error",
                "error": str(e)
            },
            "service": "voice-agent-api",
            "timestamp": datetime.utcnow().isoformat()
        }


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
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    session_id: Optional[str] = Form(None, description="Conversation session ID"),
    customer_id: Optional[str] = Form(None, description="Customer ID"),
    persona: Optional[str] = Form(None, description="Persona identifier (optional)")
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
        audio_data = await audio_file.read()
        
        # Get file format from filename or content type
        if audio_file.filename:
            file_format = audio_file.filename.split('.')[-1].lower()
        else:
            file_format = audio_file.content_type.split('/')[-1] if audio_file.content_type else "wav"
        
        result = await speech_tool.transcribe(audio_data, file_format)
        
        return VoiceInputResponse(
            success=result["success"],
            text=result.get("text"),
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
async def text_to_speech(request: VoiceOutputRequest):
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

        return VoiceOutputResponse(
            success=result["success"],
            audio_base64=result.get("audio_base64"),
            text=result.get("text", request.text),
            error=result.get("error"),
            persona=persona_config.get("id"),
            voice=result.get("voice") or selected_voice,
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
        # Ensure persona and prompt are strings or None (not Query objects)
        persona_str = None
        if persona is not None and isinstance(persona, str):
            persona_str = persona
        elif persona is not None:
            persona_str = str(persona) if persona else None
            
        prompt_str = None
        if prompt is not None and isinstance(prompt, str):
            prompt_str = prompt
        elif prompt is not None:
            prompt_str = str(prompt) if prompt else None
        
        # Use prompt if provided, otherwise fall back to persona for backward compatibility
        persona_to_use = prompt_str if prompt_str else persona_str
        session_data = conversation_tool.create_session(customer_id, persona_to_use)
        
        # Generate session ID
        import uuid
        session_id = session_data.get("session_id", str(uuid.uuid4()))
        session_data["session_id"] = session_id
        
        # Save to MongoDB
        from databases.mongodb_conversation_store import MongoDBConversationStore
        mongo_store = MongoDBConversationStore()
        await mongo_store.save_session(session_id, session_data)
        
        # Return prompt if it was provided, otherwise return persona for backward compatibility
        prompt_value = prompt if prompt else session_data.get("persona")
        
        return ConversationStartResponse(
            session_id=session_id,
            session_data=session_data,
            message="Conversation started successfully",
            persona=prompt_value,  # Using persona field for backward compatibility, but value is prompt
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
        # Get session data - use prompt if provided, otherwise persona (for backward compatibility)
        persona_name = request.prompt if request.prompt else request.persona
        
        # Load session from MongoDB if session_id provided, otherwise create new
        from databases.mongodb_conversation_store import MongoDBConversationStore
        mongo_store = MongoDBConversationStore()
        
        if request.session_id:
            session_data = await mongo_store.load_session(request.session_id)
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
            session_data, request.text, persona_name
        )
        
        # Save updated session to MongoDB
        await mongo_store.save_session(result["session_data"]["session_id"], result["session_data"])
        
        return ConversationResponse(
            response=result["response"],
            session_data=result["session_data"],
            next_state=result.get("next_state"),
            actions=result.get("actions", []),
            persona=result.get("persona"),
        )
        
    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}")
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
async def toolkit_text_to_speech(request: VoiceOutputRequest):
    """Expose the text-to-speech tool as a standalone endpoint."""
    return await text_to_speech(request)


@app.post(
    "/tools/conversation/start",
    response_model=ConversationStartResponse,
    summary="Tool: Start Conversation",
    description="Direct access to conversation session creation",
    tags=["Tools"]
)
async def toolkit_start_conversation(
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
    return await start_conversation(customer_id=customer_id, persona=persona_str)


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
# VOICE AGENT COMPLETE PIPELINE
# ============================================================================

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

        # FIRST: Check if phone number is registered in MongoDB (REQUIRED)
        if to_number:
            from databases.mongodb_phone_store import MongoDBPhoneStore
            from databases.mongodb_db import is_mongodb_available
            
            if is_mongodb_available():
                phone_store = MongoDBPhoneStore()
                logger.info(f"🔍 Looking up registered phone for: '{to_number}'")
                registered_phone = await phone_store.get_phone_by_number(to_number)
                
                if not registered_phone or registered_phone.get("isActive") == False:
                    logger.warning(f"❌ Phone number '{to_number}' is NOT registered in MongoDB")
                    logger.warning(f"   Please ensure the phone number is registered through the app UI")
                    error_response = TwilioVoiceResponse()
                    error_response.say("Sorry, this number is not registered. Please register the phone number through the app first. Goodbye.", voice="alice")
                    error_response.hangup()
                    logger.info(f"Call {call_sid} rejected: Phone number {to_number} not registered in MongoDB")
                    return HTMLResponse(content=str(error_response))
                else:
                    logger.info(f"✅ Phone number '{to_number}' is registered in MongoDB")
                    logger.info(f"   Registered phone ID: {registered_phone.get('id')}")
                    logger.info(f"   Stored as: {registered_phone.get('phoneNumber')}")
            else:
                logger.error("MongoDB is not available - cannot verify phone registration")
                error_response = TwilioVoiceResponse()
                error_response.say("Sorry, the system is temporarily unavailable. Please try again later. Goodbye.", voice="alice")
                error_response.hangup()
                logger.info(f"Call {call_sid} rejected: MongoDB not available")
                return HTMLResponse(content=str(error_response))

        # SECOND: Check if agent exists for this phone number (for both stream and batch modes)
        agent_config = None
        if to_number:
            agent_config = await twilio_phone_tool._load_agent_config(to_number)
            if not agent_config:
                logger.warning(f"❌ No active agent found for phone number {to_number}")
                error_response = TwilioVoiceResponse()
                error_response.say("Sorry, no agent is configured for this number. Please create an agent for this phone number. Goodbye.", voice="alice")
                error_response.hangup()
                logger.info(f"Call {call_sid} rejected: Number {to_number} not found in agents collection")
                return HTMLResponse(content=str(error_response))

        # Create call record in MongoDB
        try:
            from databases.mongodb_call_store import MongoDBCallStore
            call_store = MongoDBCallStore()
            await call_store.create_call(
                call_sid=call_sid,
                from_number=from_number or "unknown",
                to_number=to_number or "unknown",
                agent_id=to_number
            )
            
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
            logger.warning(f"Could not create call record: {e}")

        response = TwilioVoiceResponse()

        if TWILIO_PROCESSING_MODE == "stream":
            # --- Streaming Logic ---
            connect = response.connect()
            base_url = TWILIO_WEBHOOK_BASE_URL.split('//')[-1]
            stream_url = f"wss://{base_url}/webhooks/twilio/stream"
            
            logger.info(f"🚀 Mode: STREAM. Initiating media stream to: {stream_url}")
            stream = connect.stream(url=stream_url)
            
            # Pass call metadata to the stream handler (To number is used to identify agent)
            stream.parameter(name="From", value=call_data.get("From"))
            stream.parameter(name="To", value=call_data.get("To"))

            response.pause(length=120) # Keep call active while stream runs
        
        else:
            # --- Batch (Recording) Logic ---
            logger.info(f"📞 Mode: BATCH. Using <Record> for processing.")
            twiml_str = await twilio_phone_tool.handle_incoming_call(call_data)
            return HTMLResponse(content=twiml_str)

        return HTMLResponse(content=str(response))
        
    except Exception as e:
        logger.error(f"Error handling incoming call webhook: {e}", exc_info=True)
        error_response = TwilioVoiceResponse()
        error_response.say("Sorry, a critical application error occurred. Goodbye.")
        error_response.hangup()
        return HTMLResponse(content=str(error_response))


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
        # Get form data from Twilio webhook
        form_data = await request.form()
        status_data = dict(form_data)
        
        call_sid = status_data.get("CallSid")
        status = status_data.get("CallStatus", "unknown")
        
        logger.info(f"📞 Call status update: {call_sid} -> {status}")
        
        # Update call status in MongoDB when call ends
        if status in ["completed", "failed", "busy", "no-answer", "canceled"]:
            try:
                from databases.mongodb_call_store import MongoDBCallStore
                call_store = MongoDBCallStore()
                await call_store.end_call(call_sid)
            except Exception as e:
                logger.warning(f"Could not update call status: {e}")
        
        # Clean up stream handlers if call is ending
        if status in ["completed", "failed", "busy", "no-answer", "canceled"]:
            if call_sid and call_sid in active_stream_handlers:
                handler = active_stream_handlers[call_sid]
                logger.info(f"🧹 Cleaning up stream handler for completed call {call_sid}")
                # Remove from registry (handler will clean up its own resources)
                del active_stream_handlers[call_sid]
        
        # Process status update for batch mode
        await twilio_phone_tool.handle_call_status(status_data)
        
        return {"status": "ok", "message": "Status update processed", "call_sid": call_sid, "call_status": status}
        
    except Exception as e:
        logger.error(f"Error handling status webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
                    return HTMLResponse(content=str(response))
                
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
                    return HTMLResponse(content=str(response))
                
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
                                
                                # Add interrupt handling: Gather to detect if user starts speaking
                                # This allows the user to interrupt the AI response
                                logger.info(f"[RECORDING] Setting up interrupt detection during response")
                                from config import TWILIO_WEBHOOK_BASE_URL as WEBHOOK_BASE_INTERRUPT
                                response.gather(
                                    action=f"{WEBHOOK_BASE_INTERRUPT}/webhooks/twilio/recording?CallSid={call_sid}",
                                    method="POST",
                                    num_digits=0,  # No digits needed, just voice
                                    timeout=0.5,   # Very short timeout to detect interrupts
                                    speech_timeout="auto"  # Auto-detect when user speaks
                                )
                                logger.info(f"[RECORDING] Interrupt detection added - ready to listen")
                                
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
        twiml_response = str(response)
        logger.info(f"[RECORDING] TwiML Response length: {len(twiml_response)} bytes")
        logger.info(f"[RECORDING] Returning response to Twilio - END (conversation continues)")
        return HTMLResponse(content=twiml_response)
        
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
            return HTMLResponse(content=str(error_response))
        except Exception as inner_e:
            logger.error(f"[RECORDING] Error creating error response: {str(inner_e)}")
            # Fallback response
            return HTMLResponse(
                content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>An error occurred.</Say><Hangup/></Response>'
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


# ============================================================================
# TWILIO PHONE INTEGRATION (BATCH PROCESSING)
# ============================================================================

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
                    return HTMLResponse(content=str(response))
                
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
                    return HTMLResponse(content=str(response))
                
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
                                
                                # Add interrupt handling: Gather to detect if user starts speaking
                                # This allows the user to interrupt the AI response
                                logger.info(f"[RECORDING] Setting up interrupt detection during response")
                                from config import TWILIO_WEBHOOK_BASE_URL as WEBHOOK_BASE_INTERRUPT
                                response.gather(
                                    action=f"{WEBHOOK_BASE_INTERRUPT}/webhooks/twilio/recording?CallSid={call_sid}",
                                    method="POST",
                                    num_digits=0,  # No digits needed, just voice
                                    timeout=0.5,   # Very short timeout to detect interrupts
                                    speech_timeout="auto"  # Auto-detect when user speaks
                                )
                                logger.info(f"[RECORDING] Interrupt detection added - ready to listen")
                                
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
        twiml_response = str(response)
        logger.info(f"[RECORDING] TwiML Response length: {len(twiml_response)} bytes")
        logger.info(f"[RECORDING] Returning response to Twilio - END (conversation continues)")
        return HTMLResponse(content=twiml_response)
        
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
            return HTMLResponse(content=str(error_response))
        except Exception as inner_e:
            logger.error(f"[RECORDING] Error creating error response: {str(inner_e)}")
            # Fallback response
            return HTMLResponse(
                content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>An error occurred.</Say><Hangup/></Response>'
            )


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
@app.api_route(
    "/saas-dashboard",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    summary="SaaS Dashboard",
    description="Proxy SaaS Dashboard to Next.js",
    tags=["UI"]
)
@app.api_route(
    "/saas-dashboard/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    summary="SaaS Dashboard Routes",
    description="Proxy all SaaS dashboard routes to Next.js",
    tags=["UI"]
)
async def saas_dashboard_proxy(request: Request, path: str = ""):
    """Proxy SaaS Dashboard routes to Next.js"""
    full_path = f"saas-dashboard/{path}" if path else "saas-dashboard"
    return await proxy_to_nextjs(request, full_path)

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
    description="Create a new voice agent with configuration. Stores agent in MongoDB 'agents' collection. All configuration fields are stored including STT model, TTS model, inference model, prompts, and Twilio credentials.",
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
async def create_agent(request: Request):
    """
    Create a new agent with full configuration.
    
    **Request Body Fields:**
    - `name` (string, required): Agent name
    - `direction` (string, required): "inbound" 
    - `phoneNumber` (string, required): Phone number (e.g., "+1 555 123 4567")
    - `provider` (string, required): "twilio" or "custom"
    - `userId` (string, optional): User/tenant ID (for multi-tenant support)
    - `sttModel` (string): Speech-to-text model (default: "whisper-1")
    - `inferenceModel` (string): LLM model (default: "gpt-4o-mini")
    - `ttsModel` (string): Text-to-speech model (default: "tts-1")
    - `ttsVoice` (string): TTS voice (default: "alloy")
    - `systemPrompt` (string): System prompt for the agent
    - `greeting` (string): Initial greeting message
    - `temperature` (number): LLM temperature (0-2, default: 0.7)
    - `maxTokens` (number): Max response tokens (default: 500)
    - `active` (boolean): Enable agent to receive calls (default: true)
    - `twilioAccountSid` (string, optional): Twilio Account SID override
    - `twilioAuthToken` (string, optional): Twilio Auth Token override
    
    **Stores in MongoDB:**
    - Database: `voiceagent` (from MONGODB_DATABASE config)
    - Collection: `agents`
    - All configuration fields are persisted
    - Webhook URLs are automatically generated and stored
    """
    try:
        agent_data = await request.json()
        logger.info(f"Received agent creation request: {agent_data.get('name')} ({agent_data.get('phoneNumber')})")
        
        from databases.mongodb_agent_store import MongoDBAgentStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability
        if not is_mongodb_available():
            logger.error("MongoDB is not available for agent storage")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        agent_store = MongoDBAgentStore()
        
        # Create agent first (this returns the agent_id)
        agent_id = await agent_store.create_agent(agent_data)
        
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
        logger.info(f"💾 Agent saved to MongoDB: database='voiceagent', collection='agents'")
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
                "collection": "agents",
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
            "collection": "agents"
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
async def list_agents(active_only: Optional[bool] = Query(False, description="Only return active agents (active=true)")):
    """
    List all agents from MongoDB.
    
    **Query Parameters:**
    - `active_only` (boolean, optional): If true, only returns agents where active=true
    
    **Returns:**
    - List of agent objects with all configuration fields
    """
    try:
        from databases.mongodb_agent_store import MongoDBAgentStore
        
        agent_store = MongoDBAgentStore()
        agents = await agent_store.list_agents(active_only=active_only)
        
        return {"success": True, "agents": agents, "count": len(agents)}
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
async def register_phone(request: Request):
    """
    Register a new phone number with Twilio credentials.
    
    **Request Body Fields:**
    - `phoneNumber` (string, required): Phone number (e.g., "+1 555 123 4567")
    - `twilioAccountSid` (string, required): Twilio Account SID
    - `twilioAuthToken` (string, required): Twilio Auth Token
    - `userId` (string, optional): User/tenant ID (for multi-tenant support)
    
    **Returns:**
    - Webhook URLs (incoming and status callback) that should be configured in Twilio Console
    """
    try:
        phone_data = await request.json()
        logger.info(f"Received phone registration request for: {phone_data.get('phoneNumber')}")
        
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        # Check MongoDB availability
        if not is_mongodb_available():
            logger.error("MongoDB is not available for phone registration")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        # Validate required fields
        phone_number = phone_data.get("phoneNumber")
        twilio_account_sid = phone_data.get("twilioAccountSid")
        twilio_auth_token = phone_data.get("twilioAuthToken")
        
        if not phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required")
        if not twilio_account_sid:
            raise HTTPException(status_code=400, detail="Twilio Account SID is required")
        if not twilio_auth_token:
            raise HTTPException(status_code=400, detail="Twilio Auth Token is required")
        
        phone_store = MongoDBPhoneStore()
        
        # Generate webhook URLs (same for all phones)
        from config import TWILIO_WEBHOOK_BASE_URL
        incoming_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming"
        status_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status"
        
        # Prepare phone data
        registration_data = {
            "phoneNumber": phone_number,
            "twilioAccountSid": twilio_account_sid,
            "twilioAuthToken": twilio_auth_token,
            "webhookUrl": incoming_url,
            "statusCallbackUrl": status_url,
            "userId": phone_data.get("userId")
        }
        
        # Register phone (with duplicate validation)
        try:
            phone_id = await phone_store.register_phone(registration_data)
        except ValueError as e:
            # Duplicate phone number validation error
            logger.warning(f"❌ Duplicate phone registration attempt: {phone_number} - {str(e)}")
            raise HTTPException(status_code=409, detail=str(e))
        
        if not phone_id:
            logger.error("Failed to register phone - phone_store.register_phone returned None")
            raise HTTPException(status_code=500, detail="Failed to register phone number in MongoDB")
        
        logger.info(f"✅ Phone number registered successfully with ID: {phone_id}")
        logger.info(f"📞 Phone: {phone_number}")
        logger.info(f"🔗 Webhook URLs:")
        logger.info(f"   Incoming: {incoming_url}")
        logger.info(f"   Status: {status_url}")
        
        # Return response with webhook URLs
        return {
            "success": True,
            "phone_id": phone_id,
            "message": "Phone number registered successfully",
            "phoneNumber": phone_number,
            "webhookConfiguration": {
                "incomingUrl": incoming_url,
                "statusCallbackUrl": status_url,
                "instructions": "Configure these URLs in your Twilio Console",
                "steps": [
                    "1. Go to Twilio Console → Phone Numbers",
                    f"2. Click on phone number: {phone_number}",
                    "3. Scroll to 'Voice & Fax' section",
                    f"4. Set 'A CALL COMES IN' to: {incoming_url} (POST)",
                    f"5. Set 'STATUS CALLBACK URL' to: {status_url} (POST)",
                    "6. Click Save"
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering phone number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register phone number: {str(e)}")

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
async def list_phones(active_only: bool = Query(False, description="Only return active phones")):
    """List all registered phone numbers"""
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        logger.info(f"📞 Listing phones - active_only={active_only}")
        
        if not is_mongodb_available():
            logger.warning("MongoDB not available for listing phones")
            return {
                "success": True,
                "phones": [],
                "count": 0
            }
        
        phone_store = MongoDBPhoneStore()
        phones = await phone_store.list_phones(active_only=active_only)
        
        logger.info(f"✅ Found {len(phones)} phone(s) in MongoDB (active_only={active_only})")
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
async def delete_phone(phone_id: str = Path(..., description="MongoDB Phone ID")):
    """
    Delete a registered phone number from MongoDB (soft delete).
    
    **Path Parameters:**
    - `phone_id` (string, required): MongoDB ObjectID of the phone number
    
    **Note:** This is a soft delete - sets isDeleted=True. The phone remains in MongoDB for audit purposes.
    """
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        logger.info(f"🗑️ Deleting phone {phone_id}")
        
        if not is_mongodb_available():
            logger.error("MongoDB is not available for phone deletion")
            raise HTTPException(status_code=503, detail="MongoDB is not available. Please check MongoDB connection.")
        
        phone_store = MongoDBPhoneStore()
        success = await phone_store.delete_phone(phone_id)
        
        if success:
            logger.info(f"✅ Phone {phone_id} soft deleted successfully")
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
async def delete_agent(agent_id: str = Path(..., description="MongoDB Agent ID")):
    """
    Delete an agent from MongoDB.
    
    **Path Parameters:**
    - `agent_id` (string, required): MongoDB ObjectID of the agent
    
    **Warning:** This action is permanent and cannot be undone.
    """
    try:
        from databases.mongodb_agent_store import MongoDBAgentStore
        
        agent_store = MongoDBAgentStore()
        success = await agent_store.delete_agent(agent_id)
        
        if success:
            return {"success": True, "message": "Agent deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
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
    Fallback handler for when Media Stream doesn't work.
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
        return HTMLResponse(content=str(response))
        
    except Exception as e:
        logger.error(f"[FALLBACK] Error: {str(e)}")
        from twilio.twiml.voice_response import VoiceResponse
        error_response = VoiceResponse()
        error_response.say("Sorry, an error occurred. Goodbye.")
        error_response.hangup()
        return HTMLResponse(content=str(error_response))

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
    limit: int = Query(100, description="Maximum number of calls to return", ge=1, le=1000)
):
    """Get all calls with transcripts"""
    try:
        from databases.mongodb_call_store import MongoDBCallStore
        call_store = MongoDBCallStore()
        
        # Map UI status to DB status
        db_status = None
        if status == "ongoing":
            db_status = "active"
        elif status == "finished":
            db_status = "completed"
        elif status:
            db_status = status
        
        calls = await call_store.get_all_calls(
            agent_id=agent_id,
            status=db_status,
            limit=limit
        )
        
        return {"calls": calls}
        
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
