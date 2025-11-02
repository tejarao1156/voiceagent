from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Path, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import json
import logging
from datetime import datetime

# Import all models from the unified models file
from models import (
    # Database models
    Base, Customer, ConversationSession,
    # API schemas
    HealthResponse, RootResponse,
    VoiceInputRequest, VoiceInputResponse, VoiceOutputRequest, VoiceOutputResponse,
    ConversationRequest, ConversationResponse, ConversationStartRequest, ConversationStartResponse,
    VoiceAgentProcessResponse, PersonaSummary,
    ErrorResponse, SuccessResponse,
    PaginationRequest, PaginationResponse
)

from database import get_db, create_tables
from voice_processor import VoiceProcessor
from conversation_manager import ConversationManager, ConversationState
from models import Customer, ConversationSession
from config import DEBUG
from tools import SpeechToTextTool, TextToSpeechTool, ConversationalResponseTool
from realtime_websocket import realtime_agent
from personas import get_persona_config, list_personas

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
    1. Set up your `.env` file with OpenAI API key and database credentials
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
            "url": "http://localhost:8000",
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

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Database tables created successfully")

# ============================================================================
# GENERAL ENDPOINTS
# ============================================================================

@app.get(
    "/",
    response_model=RootResponse,
    summary="Root Endpoint",
    description="Get basic API information and status",
    tags=["General"]
)
async def root():
    """Root endpoint with API information"""
    return RootResponse(
        message="Voice Agent API",
        version="1.0.0",
        status="running",
        documentation="/docs",
        health_check="/health"
    )

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
    curl -X POST "http://localhost:8000/voice/speech-to-text" \
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
    curl -X POST "http://localhost:8000/voice/text-to-speech" \
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
    persona: Optional[str] = Query(None, description="Persona identifier"),
    db: Session = Depends(get_db)
):
    """
    Start a new conversation session.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:8000/conversation/start?customer_id=customer123"
    ```
    """
    try:
        session_data = conversation_tool.create_session(customer_id, persona)
        
        # Save session to database
        db_session = ConversationSession(
            customer_id=customer_id,
            session_data=json.dumps(session_data),
            status="active"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        session_data["id"] = db_session.id
        
        return ConversationStartResponse(
            session_id=db_session.id,
            session_data=session_data,
            message="Conversation started successfully",
            persona=session_data.get("persona"),
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
    request: ConversationRequest,
    db: Session = Depends(get_db)
):
    """
    Process user input and generate appropriate response.
    
    **Example usage**:
    ```bash
    curl -X POST "http://localhost:8000/conversation/process" \
         -H "Content-Type: application/json" \
         -d '{"text": "I want to order a pizza", "session_id": "session123"}'
    ```
    """
    try:
        # Get session data
        persona_name = request.persona

        if request.session_id:
            db_session = db.query(ConversationSession).filter(
                ConversationSession.id == request.session_id
            ).first()
            
            if not db_session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session_data = json.loads(db_session.session_data)
            if not persona_name:
                persona_name = session_data.get("persona")
        else:
            # Create new session if none provided
            session_data = conversation_tool.create_session(request.customer_id, persona_name)
        
        # Process user input (general conversation)
        result = await conversation_tool.generate_response(
            session_data, request.text, persona_name
        )
        
        # Update session in database
        if request.session_id:
            db_session.session_data = json.dumps(result["session_data"])
            db.commit()
        
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
    persona: Optional[str] = Query(None, description="Persona identifier"),
    db: Session = Depends(get_db)
):
    """Expose conversation session creation for testing."""
    return await start_conversation(customer_id=customer_id, persona=persona, db=db)


@app.post(
    "/tools/conversation/process",
    response_model=ConversationResponse,
    summary="Tool: Conversation Response",
    description="Direct access to the conversation response generator",
    tags=["Tools"]
)
async def toolkit_process_conversation(
    request: ConversationRequest,
    db: Session = Depends(get_db)
):
    """Expose the conversation response tool as a standalone endpoint."""
    return await process_conversation(request, db)


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
    persona: Optional[str] = Form(None, description="Persona identifier"),
    db: Session = Depends(get_db)
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
    curl -X POST "http://localhost:8000/voice-agent/process" \
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
            db
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
    const ws = new WebSocket('ws://localhost:8000/ws/voice-agent/session123');
    
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
    curl "http://localhost:8000/ws/status"
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
    curl -X POST "http://localhost:8000/ws/disconnect/session123"
    ```
    """
    try:
        await realtime_agent.disconnect(session_id)
        return {"message": f"Session {session_id} disconnected successfully"}
    except Exception as e:
        logger.error(f"Error disconnecting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ERROR HANDLERS
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
