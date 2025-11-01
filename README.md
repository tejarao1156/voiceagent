# General Voice Agent Backend System

A general-purpose voice agent backend system built with FastAPI, OpenAI, and PostgreSQL.

## Features

- **Speech-to-Text**: Convert voice input to text using OpenAI Whisper
- **Text-to-Speech**: Generate natural voice responses using OpenAI TTS
- **Conversation Management**: Intelligent conversation flow with state tracking
- **Real-time Processing**: WebSocket support for live voice interaction
- **General Purpose**: Designed for any conversation use case
- **REST API**: Comprehensive API for all voice agent operations
- **Database Models**: Complete data models for conversation sessions

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Voice Agent   │    │   Database      │
│   (WebSocket)   │◄──►│   Backend       │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   OpenAI APIs   │
                       │   (Whisper/TTS) │
                       └─────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `dev.env` to `.env` for development:

```bash
cp dev.env .env
```

Then edit `.env` and fill in your actual configuration values:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: Your Supabase PostgreSQL connection string

**Supabase Setup:**
1. Create a new project at [supabase.com](https://supabase.com)
2. Go to Project Settings > Database > Connection string
3. Copy the connection string and replace `[password]` with your database password
4. Update `DATABASE_URL` in your `.env` file

### 3. Setup Database

First, test your Supabase connection:

```bash
python test_supabase_connection.py
```

If the connection test passes, create the database tables:

```bash
python -c "from database import create_tables; create_tables()"
```

### 4. Run the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

The API is fully documented with Swagger/OpenAPI documentation. Once the server is running, visit:

- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### API Endpoints Overview

#### 🎤 Voice Processing
- `POST /voice/speech-to-text` - Convert audio to text using OpenAI Whisper
- `POST /voice/text-to-speech` - Convert text to audio using OpenAI TTS
- `POST /voice-agent/process` - Complete voice agent pipeline

#### 💬 Conversation Management
- `POST /conversation/start` - Start new conversation session
- `POST /conversation/process` - Process user input and generate response

#### 🔧 General
- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint

#### ⚡ Real-time (WebSocket)
- `WS /ws/voice-agent/{session_id}` - Real-time voice agent WebSocket
- `GET /ws/status` - Get WebSocket connection status
- `POST /ws/disconnect/{session_id}` - Disconnect WebSocket session

## Usage Examples

### Basic Voice Agent Interaction

```python
import requests

# Start conversation
response = requests.post("http://localhost:8000/conversation/start", 
                        json={"customer_id": "customer123"})
session_id = response.json()["session_id"]

# Process voice input
with open("audio.wav", "rb") as f:
    response = requests.post("http://localhost:8000/voice-agent/process",
                           files={"audio_file": f},
                           data={"session_id": session_id})
    
    result = response.json()
    print(f"User said: {result['user_input']}")
    print(f"Agent responded: {result['agent_response']}")
```

### Real-time Voice Agent (WebSocket)

```javascript
// Connect to real-time voice agent
const ws = new WebSocket('ws://localhost:8000/ws/voice-agent/session123');

ws.onopen = function(event) {
    console.log('Connected to voice agent');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'transcription':
            console.log('You said:', data.text);
            break;
        case 'conversation_response':
            console.log('Agent:', data.text);
            break;
        case 'audio_response':
            // Play the audio response
            const audio = new Audio('data:audio/mp3;base64,' + data.audio_base64);
            audio.play();
            break;
    }
};

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
```

### HTML Client Demo

Open `realtime_client.html` in your browser for a complete real-time voice agent demo with:
- Real-time audio recording and processing
- Text input support
- Voice responses
- Visual conversation history

## Database Schema

### Core Tables

- **customers**: Customer information and contact details
- **conversation_sessions**: Conversation state and history

## Development

### Project Structure

```
voiceagent/
├── main.py                 # Main entry point (runs api_general.py)
├── api_general.py         # Complete FastAPI application with Swagger docs
├── models.py              # Unified database models and API schemas
├── database.py            # Database configuration
├── voice_processor.py     # Speech-to-text and text-to-speech
├── conversation_manager.py # Conversation flow management
├── realtime_websocket.py  # Real-time WebSocket handler
├── realtime_client.html   # HTML client for real-time demo
├── config.py             # Configuration management
├── dev.env               # Complete development environment configuration
├── env.example           # Environment configuration template
└── requirements.txt      # Python dependencies
```

### Adding New Features

1. **Custom Voice Models**: Update `VoiceProcessor` class
2. **New Conversation States**: Add to `ConversationState` enum
3. **Additional Endpoints**: Add to `api_general.py`
4. **Database Changes**: Update `models.py` and run migrations

## Production Deployment

### Environment Setup

1. Use production PostgreSQL database
2. Configure Redis for session management
3. Set up proper logging and monitoring
4. Use HTTPS for webhook endpoints
5. Implement rate limiting and security measures

### Scaling Considerations

- Use Redis for session storage in multi-instance deployments
- Implement database connection pooling
- Add caching for menu items and customer data
- Consider using Celery for background tasks

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**: Check API key and rate limits
2. **Database Connection**: Verify PostgreSQL is running and accessible
3. **Audio Format Issues**: Ensure supported audio formats (WAV, MP3)
4. **Phone Integration**: Verify Twilio credentials and webhook URLs

### Logs

Check application logs for detailed error information:

```bash
tail -f logs/voice_agent.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License.
