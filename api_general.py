from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Path, WebSocket, WebSocketDisconnect
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from typing import Optional, Dict, Any, List
import json
import logging
import asyncio
from datetime import datetime

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

# Startup event - no database initialization
@app.on_event("startup")
async def startup_event():
    logger.info("Voice Agent API started (running without database - using in-memory sessions)")

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
                <a href="/chat" class="link">🎤 Chat UI - Voice Conversation</a>
                <a href="/dashboard" class="link">📞 Twilio Dashboard</a>
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
        # Use prompt if provided, otherwise fall back to persona for backward compatibility
        persona_to_use = prompt if prompt else persona
        session_data = conversation_tool.create_session(customer_id, persona_to_use)
        
        # Use in-memory session ID
        session_id = session_data.get("session_id", "mem_" + str(hash(str(session_data))))
        
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
        
        # Create new session (in-memory only)
        session_data = conversation_tool.create_session(request.customer_id, persona_name)
        
        # Process user input (general conversation) - streaming enabled for faster response
        result = await conversation_tool.generate_response(
            session_data, request.text, persona_name
        )
        
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
    return await start_conversation(customer_id=customer_id, persona=persona)


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

@app.post(
    "/webhooks/twilio/incoming",
    summary="Twilio Incoming Call Webhook",
    description="Handle incoming phone calls from Twilio",
    tags=["Twilio Phone Integration"]
)
async def twilio_incoming_call(request: Request):
    """
    Webhook endpoint for incoming Twilio phone calls.
    
    When a call comes in, Twilio sends a POST request to this endpoint.
    The endpoint returns TwiML instructions to start a Media Stream,
    which enables real-time bidirectional audio processing.
    
    **Configuration:**
    1. Set up your Twilio phone number
    2. Configure webhook URL in Twilio Console:
       - Voice & Fax → Phone Numbers → [Your Number] → Configure
       - Set "A CALL COMES IN" webhook to: `https://your-domain.com/webhooks/twilio/incoming`
    
    **Example Twilio Console Setup:**
    ```
    Webhook URL: https://your-domain.com/webhooks/twilio/incoming
    HTTP Method: POST
    ```
    
    **For Local Development:**
    Use ngrok to expose your local server:
    ```bash
    ngrok http 4002
    # Then use: https://your-ngrok-url.ngrok.io/webhooks/twilio/incoming
    ```
    """
    try:
        # Get form data from Twilio webhook
        form_data = await request.form()
        call_data = dict(form_data)
        
        logger.info(f"Received incoming call webhook: {call_data.get('CallSid')}")
        
        # Process the call and get TwiML response
        twiml = await twilio_phone_tool.handle_incoming_call(call_data)
        
        # Return TwiML response
        from fastapi.responses import Response
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error handling incoming call webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Process status update
        await twilio_phone_tool.handle_call_status(status_data)
        
        return {"status": "ok", "message": "Status update processed"}
        
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
                from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
                
                # Try downloading with .wav extension first
                recording_url_wav = recording_url + ".wav"
                
                # Create basic auth header
                auth_string = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}"
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
                stt_result = await speech_tool.transcribe(audio_data, "wav")
                
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
                        # Get AI response
                        session_id = twilio_phone_tool.active_calls.get(call_sid)
                        if session_id:
                            session_data = twilio_phone_tool.session_data.get(session_id, {})
                            ai_response = await conversation_tool.generate_response(
                                session_data, user_text, None
                            )
                            response_text = ai_response.get("response", "I'm sorry, I didn't understand that.")
                        else:
                            response_text = "I'm sorry, I couldn't process your request."
                        
                        logger.info(f"[RECORDING] AI Response: {response_text}")
                        
                        # Convert response to speech
                        tts_result = await tts_tool.synthesize(response_text, voice="alloy", parallel=False)
                        
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

@app.websocket("/webhooks/twilio/stream")
async def twilio_media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Stream.
    
    This endpoint handles real-time bidirectional audio streaming:
    - Receives audio from the phone call (μ-law PCM format)
    - Processes audio through your AI tools:
      * Speech-to-Text (OpenAI Whisper)
      * Conversation AI (GPT)
      * Text-to-Speech (OpenAI TTS)
    - Sends audio back to the phone call
    
    **How it works:**
    1. Twilio connects to this WebSocket when Media Stream starts
    2. Audio flows bidirectionally in real-time
    3. Your AI processes the conversation automatically
    
    **Message Format:**
    - Incoming: JSON events + base64-encoded audio payloads
    - Outgoing: JSON events + base64-encoded audio payloads
    
    **Note:** This endpoint is called automatically by Twilio when
    a Media Stream is started via the TwiML response from
    `/webhooks/twilio/incoming`. The CallSid is extracted from
    the Media Stream messages.
    """
    try:
        logger.info("Media Stream WebSocket connection received")
        
        # Try to get CallSid from query params (some Twilio setups pass it)
        query_params = dict(websocket.query_params)
        call_sid = query_params.get("CallSid") or query_params.get("call_sid")
        
        if not call_sid:
            # CallSid will be extracted from Media Stream messages by the tool
            logger.debug("No CallSid in query params, will extract from stream messages")
            call_sid = None
        
        # Handle the Media Stream (tool will accept websocket and extract CallSid if needed)
        await twilio_phone_tool.handle_media_stream(websocket, call_sid)
        
    except WebSocketDisconnect:
        logger.info("Media Stream WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in Media Stream WebSocket: {str(e)}")
        try:
            await websocket.close()
        except:
            pass

@app.get(
    "/dashboard",
    summary="Twilio Phone Dashboard",
    description="HTML dashboard for monitoring Twilio phone calls",
    tags=["Twilio Phone Integration"],
    response_class=HTMLResponse
)
async def dashboard():
    """Serve the Twilio phone dashboard UI."""
    import os
    dashboard_path = os.path.join(os.path.dirname(__file__), "ui", "twilio_phone_ui.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get(
    "/twilio/dashboard",
    summary="Twilio Phone Dashboard (Legacy)",
    description="HTML dashboard for monitoring Twilio phone calls (legacy endpoint)",
    tags=["Twilio Phone Integration"],
    response_class=HTMLResponse
)
async def twilio_dashboard():
    """Serve the Twilio phone dashboard UI (legacy endpoint)."""
    import os
    dashboard_path = os.path.join(os.path.dirname(__file__), "ui", "twilio_phone_ui.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")

@app.get(
    "/chat",
    summary="Chat UI",
    description="Conversation chat UI with voice and text support",
    tags=["UI"],
    response_class=HTMLResponse
)
async def chat_ui():
    """Serve the chat UI."""
    import os
    chat_path = os.path.join(os.path.dirname(__file__), "ui", "chat_ui.html")
    if os.path.exists(chat_path):
        return FileResponse(chat_path)
    else:
        raise HTTPException(status_code=404, detail="Chat UI not found")

@app.get(
    "/ui/chat",
    summary="Chat UI (Legacy)",
    description="Conversation chat UI with voice and text support (legacy endpoint)",
    tags=["UI"],
    response_class=HTMLResponse
)
async def chat_ui_legacy():
    """Serve the chat UI (legacy endpoint - redirects to /chat)."""
    import os
    chat_path = os.path.join(os.path.dirname(__file__), "ui", "chat_ui.html")
    if os.path.exists(chat_path):
        return FileResponse(chat_path)
    else:
        raise HTTPException(status_code=404, detail="Chat UI not found")

@app.get(
    "/twilio/status",
    summary="Get Twilio Call Status",
    description="Get status of active Twilio calls and configuration",
    tags=["Twilio Phone Integration"]
)
async def get_twilio_status():
    """Get current status of Twilio integration."""
    from config import TWILIO_ACCOUNT_SID, TWILIO_PHONE_NUMBER, TWILIO_WEBHOOK_BASE_URL
    
    return {
        "configured": bool(TWILIO_ACCOUNT_SID and TWILIO_PHONE_NUMBER),
        "phone_number": TWILIO_PHONE_NUMBER,
        "account_sid": TWILIO_ACCOUNT_SID[:10] + "..." if TWILIO_ACCOUNT_SID else None,
        "webhook_base_url": TWILIO_WEBHOOK_BASE_URL,
        "active_calls": len(twilio_phone_tool.active_calls),
        "active_call_sids": list(twilio_phone_tool.active_calls.keys()),
        "server_status": "online"
    }

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
