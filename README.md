# General Voice Agent Backend System

A general-purpose voice agent backend system built with FastAPI, OpenAI, and PostgreSQL.

## Features

- **Speech-to-Text**: Convert voice input to text using OpenAI Whisper
- **Text-to-Speech**: Generate natural voice responses using OpenAI TTS
- **Conversation Management**: Intelligent conversation flow with state tracking
- **Real-time Processing**: WebSocket support for live voice interaction
- **Phone Integration**: Twilio Voice API integration for AI phone conversations
- **General Purpose**: Designed for any conversation use case
- **REST API**: Comprehensive API for all voice agent operations
- **Database Models**: Complete data models for conversation sessions
- **Persona System**: Choose configurable personas that tailor tone and TTS voices

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

Copy `env.example` to `.env` for development:

```bash
cp env.example .env
```

Then edit `.env` and fill in your actual configuration values:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: Your Supabase PostgreSQL connection string
- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID (for phone integration)
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number (e.g., +1234567890)
- `TWILIO_WEBHOOK_BASE_URL`: Base URL for webhooks (e.g., https://your-domain.com)

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

### 4. Run the API Server

```bash
./start_api.sh
# or python main.py
```

The API will be available at `http://localhost:4000`.

### 5. Run the Web UI (optional)

```bash
./start_ui.sh
# or: cd ui && npm install && npm run dev
```

The UI will be available at `http://localhost:9000` (proxied through `ui/server.js`).

### 6. Run API and UI Together

```bash
./start_all.sh
```

This script launches both servers in parallel; use `Ctrl+C` to stop them.

### 7. List Personas

```bash
curl http://localhost:4000/personas
```

Use the returned persona identifier (for example `friendly_guide`, `calm_concierge`, `energetic_host`) when calling conversation or TTS endpoints.

## API Documentation

The API is fully documented with Swagger/OpenAPI documentation. Once the server is running, visit:

- **Interactive API Docs**: `http://localhost:4000/docs`
- **ReDoc Documentation**: `http://localhost:4000/redoc`
- **OpenAPI Schema**: `http://localhost:4000/openapi.json`

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
- `GET /personas` - List available personas with voices and descriptions
- `GET /personas/{persona}` - Retrieve a specific persona profile

#### ⚡ Real-time (WebSocket)
- `WS /ws/voice-agent/{session_id}` - Real-time voice agent WebSocket
- `GET /ws/status` - Get WebSocket connection status
- `POST /ws/disconnect/{session_id}` - Disconnect WebSocket session

#### 📞 Twilio Phone Integration
- `POST /webhooks/twilio/incoming` - Handle incoming phone calls
- `POST /webhooks/twilio/status` - Handle call status updates
- `WS /webhooks/twilio/stream` - Real-time Media Stream for bidirectional audio

#### 🧰 Tools
- `POST /tools/understanding/speech-to-text` - Direct speech-to-text tool access
- `POST /tools/response/text-to-speech` - Direct text-to-speech tool access
- `POST /tools/conversation/start` - Create conversation sessions via tool interface
- `POST /tools/conversation/process` - Generate conversation responses via tool interface

## Usage Examples

### Basic Voice Agent Interaction

```python
import requests

PERSONA = "friendly_guide"

# Start conversation with a specific persona
response = requests.post(
    "http://localhost:4000/conversation/start",
    params={"customer_id": "customer123", "persona": PERSONA},
)
response.raise_for_status()
session_id = response.json()["session_id"]

# Process voice input end-to-end (STT → conversation → TTS)
with open("audio.wav", "rb") as source_audio:
    response = requests.post(
        "http://localhost:4000/voice-agent/process",
        files={"audio_file": source_audio},
        data={"session_id": session_id, "persona": PERSONA},
    )

response.raise_for_status()
result = response.json()
print(f"User said: {result['user_input']}")
print(f"Agent responded: {result['agent_response']}")
print(f"Persona: {result['persona']}   Voice: {result['voice']}")
```

### Real-time Voice Agent (WebSocket)

```javascript
// Connect to real-time voice agent
const ws = new WebSocket('ws://localhost:4000/ws/voice-agent/session123');

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

### HTML Client Demos

**Available UIs (Access via your server):**

Once your server is running (`python main.py`), access these UIs:

1. **Chat UI** - `http://localhost:4002/ui/chat`
   - Conversation interface with text input and voice response
   - Type your message (prompt) and get AI response as speech
   - Voice recording support
   - Visual conversation history
   - Clean, simple interface

2. **Twilio Phone Dashboard** - `http://localhost:4002/twilio/dashboard`
   - Monitor and manage Twilio phone calls
   - View active calls and configuration status
   - Test webhook endpoints
   - Activity logs and call tracking

**Direct File Access:**
- `ui/chat_ui.html` - Chat UI (open directly in browser)
- `ui/twilio_phone_ui.html` - Twilio dashboard (open directly)

### Twilio Phone Integration

#### Quick Reference: What You Need

**Credentials to Get from Twilio:**
1. **Account SID** - Found on Twilio Console dashboard (starts with "AC")
2. **Auth Token** - Found on Twilio Console dashboard (click to reveal)
3. **Phone Number** - Purchase or use trial number (format: +1234567890)

**Configuration Needed:**
1. **`.env` file** - Add 4 Twilio variables (see Step 4)
2. **Public URL** - For webhooks (ngrok for local, domain for production)
3. **Twilio Console** - Configure webhook URLs (see Step 6)

**Already Have:**
- ✅ OpenAI API Key (already in your system)
- ✅ Database (already configured)

---

#### Complete Setup Checklist

**What You Need to Get:**

1. ✅ **Twilio Account** (Free trial available)
2. ✅ **Twilio Account SID** (from Twilio Console)
3. ✅ **Twilio Auth Token** (from Twilio Console)
4. ✅ **Twilio Phone Number** (purchase or use trial number)
5. ✅ **Public URL** (for webhooks - ngrok for local, domain for production)
6. ✅ **OpenAI API Key** (already configured)
7. ✅ **Database** (already configured)

#### Step-by-Step Setup

**Step 1: Create Twilio Account**

1. Go to [twilio.com](https://www.twilio.com/try-twilio)
2. Sign up for a free account (no credit card needed for trial)
3. Verify your email and phone number

**Step 2: Get Your Twilio Credentials**

1. Log in to [Twilio Console](https://console.twilio.com)
2. You'll see your **Account SID** on the dashboard (looks like: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
3. Click on it to reveal your **Auth Token** (looks like: `your_auth_token_here`)
   - ⚠️ **Important**: Copy and save these - Auth Token is only shown once!
4. Keep these credentials secure - you'll need them for your `.env` file

**Step 3: Get a Phone Number**

1. In Twilio Console, go to **Phone Numbers** → **Manage** → **Buy a number**
2. For trial accounts:
   - You get a free phone number automatically
   - Or search for available numbers in your country
3. Click **Buy** to purchase (or use the trial number)
4. Copy your phone number (format: `+1234567890`)

**Step 4: Register Phone Number Through App UI**

⚠️ **IMPORTANT**: Twilio credentials MUST be registered through the app UI, NOT in `.env` file.

1. **Start your server:**
   ```bash
   python main.py
   ```

2. **Open the app UI** and navigate to "AI Agents" section

3. **Click "Register Phone Number"** button (beside "Create Agent")

4. **Enter your Twilio credentials:**
   - Phone Number: Your Twilio phone number (e.g., +1234567890)
   - Twilio Account SID: From Twilio Console Dashboard (starts with "AC")
   - Twilio Auth Token: From Twilio Console Dashboard (click "Show Token")

5. **Click "Register Phone"** - the system will:
   - Store credentials securely in MongoDB
   - Generate webhook URLs for you to configure in Twilio Console
   - Display instructions on how to configure webhooks

**Where to find each value:**
- `Phone Number`: Your purchased Twilio number (format: +1234567890)
- `Twilio Account SID`: Dashboard → Account Info (starts with "AC")
- `Twilio Auth Token`: Dashboard → Account Info → Auth Token (click to reveal)

**Note**: The system will ONLY pull credentials from MongoDB, not from `.env` file.

**Step 5: Set Up Public URL (Webhook Access)**

**For Local Development (using ngrok):**

1. **Install ngrok:**
   ```bash
   # macOS
   brew install ngrok
   
   # Or download from: https://ngrok.com/download
   ```

2. **Start your server:**
   ```bash
   python main.py
   # Server runs on http://localhost:4002
   ```

3. **In another terminal, start ngrok:**
   ```bash
   ngrok http 4002
   ```

4. **Copy the HTTPS URL:**
   - You'll see something like: `https://abc123.ngrok.io`
   - Copy this URL

5. **Update `.env` file:**
   ```bash
   TWILIO_WEBHOOK_BASE_URL=https://abc123.ngrok.io
   ```

6. **⚠️ Important**: 
   - ngrok URL changes each time you restart (free version)
   - You'll need to update Twilio webhook URL each time
   - For production, use a permanent domain

**For Production:**

1. Deploy your server to a cloud platform (Heroku, AWS, GCP, etc.)
2. Get your public HTTPS URL: `https://your-domain.com`
3. Update `.env`:
   ```bash
   TWILIO_WEBHOOK_BASE_URL=https://your-domain.com
   ```
4. Make sure HTTPS is enabled (required by Twilio)

#### Configure Twilio Console

**Step 6: Configure Phone Number Webhooks**

1. **Go to Twilio Console:**
   - Navigate to: [Phone Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
   - Or: **Phone Numbers** → **Manage** → **Active Numbers**

2. **Click on your phone number** (the one you purchased/assigned)

3. **Configure "A CALL COMES IN" webhook:**
   - Scroll to **Voice & Fax** section
   - Find **"A CALL COMES IN"** field
   - Set webhook URL: 
     ```
     https://your-domain.com/webhooks/twilio/incoming
     ```
     (Replace with your actual URL from Step 5)
   - Set HTTP method: **POST** (from dropdown)
   - Click **Save** button at the bottom

4. **Configure "STATUS CALLBACK URL" (Optional but recommended):**
   - In the same page, scroll to **"STATUS CALLBACK URL"** field
   - Set webhook URL:
     ```
     https://your-domain.com/webhooks/twilio/status
     ```
   - Set HTTP method: **POST**
   - Click **Save**

**Visual Guide:**
```
Twilio Console → Phone Numbers → [Your Number] → Configure
├─ Voice & Fax
│  ├─ A CALL COMES IN
│  │  ├─ URL: https://your-domain.com/webhooks/twilio/incoming
│  │  └─ Method: POST
│  └─ STATUS CALLBACK URL
│     ├─ URL: https://your-domain.com/webhooks/twilio/status
│     └─ Method: POST
└─ Save
```

**Step 7: Verify Your Configuration**

1. **Verify phone number is registered:**
   - Check the app UI "AI Agents" section
   - Your registered phone number should appear in the list
   - You can use it when creating agents

2. **Verify webhook URLs are configured in Twilio Console:**
   - Go to Twilio Console → Phone Numbers → [Your Number]
   - Check that "A CALL COMES IN" webhook is set correctly
   - Check that "STATUS CALLBACK URL" is set correctly

3. **Test the webhook endpoint:**
   ```bash
   # Test if webhook is accessible
   curl https://your-domain.com/webhooks/twilio/incoming
   # Should return TwiML or error (not 404)
   ```

4. **Make a test call:**
   - Call your Twilio phone number
   - Check server logs for incoming webhook
   - You should see: "Received incoming call webhook: CA..."

#### How It Works

```
Incoming Phone Call
    ↓
Twilio → POST /webhooks/twilio/incoming
    ↓
Server returns TwiML → Starts Media Stream
    ↓
Twilio connects to WebSocket → /webhooks/twilio/stream
    ↓
Real-time Audio Processing:
  Phone Audio (μ-law PCM) 
    ↓
  Convert to WAV → SpeechToTextTool (OpenAI Whisper)
    ↓
  ConversationalResponseTool (GPT) → Generate AI response
    ↓
  TextToSpeechTool (OpenAI TTS) → Generate audio
    ↓
  Convert to μ-law PCM → Send back to Twilio → Phone
```

#### Architecture Details

**TwilioPhoneTool** (`tools/phone/twilio_phone/`):
- Handles incoming call webhooks
- Manages Media Stream WebSocket connections
- Converts audio formats (Twilio μ-law ↔ WAV for OpenAI)
- Integrates with existing tools:
  - `SpeechToTextTool` - Transcribes caller's speech
  - `ConversationalResponseTool` - Generates AI responses
  - `TextToSpeechTool` - Converts responses to speech

**Audio Processing Pipeline**:
1. **Incoming Audio**: Twilio sends μ-law PCM at 8000Hz
2. **Format Conversion**: Convert to WAV at 16000Hz for OpenAI Whisper
3. **Speech-to-Text**: Use OpenAI Whisper to transcribe
4. **Conversation**: Use GPT to generate response
5. **Text-to-Speech**: Use OpenAI TTS to generate audio
6. **Format Conversion**: Convert back to μ-law PCM for Twilio
7. **Outgoing Audio**: Send back through Media Stream

#### Complete Configuration Summary

**Required Environment Variables (.env file):**

```bash
# Essential for Twilio Integration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_from_twilio
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_BASE_URL=https://your-domain.com

# Also Required (already in your system)
OPENAI_API_KEY=sk-...your-openai-key...
DATABASE_URL=postgresql://...your-database-url...
```

**Twilio Console Settings:**

1. **Phone Number Configuration:**
   - A CALL COMES IN: `https://your-domain.com/webhooks/twilio/incoming` (POST)
   - STATUS CALLBACK: `https://your-domain.com/webhooks/twilio/status` (POST)

#### Testing the Integration

**Step 8: Test the Complete Integration**

1. **Start Your Server:**
   ```bash
   python main.py
   # Server should start on http://localhost:4002 (or port from config)
   ```

2. **For Local Testing (if using ngrok):**
   ```bash
   # In another terminal window
   ngrok http 4002
   # You'll see: Forwarding https://abc123.ngrok.io -> http://localhost:4002
   ```

3. **Update `.env` with ngrok URL (if local):**
   ```bash
   TWILIO_WEBHOOK_BASE_URL=https://abc123.ngrok.io
   ```

4. **Update Twilio Console webhook URL:**
   - Go to Phone Numbers → Your Number → Configure
   - Update "A CALL COMES IN" to: `https://abc123.ngrok.io/webhooks/twilio/incoming`
   - Click Save

5. **Make a Test Call:**
   - Call your Twilio phone number from any phone
   - You should hear the AI greeting
   - Speak naturally - the AI will respond
   - Check server logs for:
     - "Received incoming call webhook: CA..."
     - "Media Stream connected for call: CA..."
     - "User said: ..."
     - "Agent responding: ..."

6. **Verify Logs:**
   ```bash
   # Watch server logs for:
   # ✅ Incoming call webhook received
   # ✅ Media Stream connected
   # ✅ Audio processing (STT → Conversation → TTS)
   # ✅ Audio sent back to caller
   ```

**Quick Test Checklist:**

- [ ] Server starts without errors
- [ ] `.env` file has all Twilio credentials
- [ ] Webhook URL is accessible (test with curl)
- [ ] Twilio Console webhook is configured
- [ ] Can make a call to your Twilio number
- [ ] Server logs show incoming webhook
- [ ] Media Stream connects
- [ ] Can hear AI responses

#### Troubleshooting

**Common Issues:**

1. **Webhook Not Receiving Calls**
   - Verify webhook URL is accessible (HTTPS required)
   - Check Twilio Console webhook configuration
   - Test webhook URL manually: `curl https://your-domain.com/webhooks/twilio/incoming`
   - Check server logs for incoming requests

2. **Media Stream Not Connecting**
   - Verify `TWILIO_WEBHOOK_BASE_URL` is set correctly
   - Ensure WebSocket endpoint is accessible
   - Check firewall/network settings
   - Review Twilio Media Stream logs in Twilio Console

3. **Audio Quality Issues**
   - Verify audio format conversion is working
   - Check sample rate conversion (8000Hz ↔ 16000Hz)
   - Ensure OpenAI API keys are valid
   - Review audio buffer settings

4. **No Audio in Call**
   - Check if TTS is generating audio
   - Verify audio format conversion
   - Ensure Media Stream is sending audio chunks
   - Review Twilio call logs for errors

5. **AI Not Responding**
   - Check OpenAI API key and rate limits
   - Verify conversation tool is working
   - Review error logs for STT/TTS failures
   - Test individual tools separately

#### Production Deployment

**Important Considerations:**

1. **HTTPS Required**: Twilio requires HTTPS for webhooks
   - Use a reverse proxy (nginx, Traefik)
   - Or deploy to cloud platform (Heroku, AWS, GCP, etc.)

2. **Security**
   - Validate Twilio webhook signatures (recommended)
   - Use environment variables for credentials
   - Implement rate limiting
   - Monitor for abuse

3. **Performance**
   - Media Streams require persistent WebSocket connections
   - Consider connection pooling for multiple calls
   - Monitor audio processing latency
   - Optimize buffer sizes for your use case

4. **Scaling**
   - Media Streams are stateful (one connection per call)
   - Each call requires server resources
   - Consider load balancing strategies
   - Monitor concurrent call capacity

#### API Endpoints Reference

**POST /webhooks/twilio/incoming**
- Receives incoming call webhook from Twilio
- Returns TwiML XML to start Media Stream
- Creates conversation session

**POST /webhooks/twilio/status**
- Receives call status updates
- Tracks call lifecycle (ringing, answered, completed, etc.)
- Cleans up resources when call ends

**WebSocket /webhooks/twilio/stream**
- Handles real-time bidirectional audio
- Processes audio through AI tools
- Sends responses back to caller
- Automatically connected by Twilio when Media Stream starts

#### Implementation Details

This section explains how the Twilio phone integration is implemented under the hood.

**Architecture Overview:**

```
┌─────────────┐
│ Phone Call  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Twilio Voice API                       │
│  - Receives call                        │
│  - Sends webhook to our server         │
│  - Connects Media Stream WebSocket     │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Our Server (FastAPI)                   │
│  ├─ POST /webhooks/twilio/incoming      │
│  ├─ POST /webhooks/twilio/status        │
│  └─ WS /webhooks/twilio/stream          │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  TwilioPhoneTool                        │
│  ├─ handle_incoming_call()              │
│  ├─ handle_media_stream()               │
│  └─ process_phone_audio()               │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Your Existing Tools                    │
│  ├─ SpeechToTextTool (OpenAI Whisper)   │
│  ├─ ConversationalResponseTool (GPT)    │
│  └─ TextToSpeechTool (OpenAI TTS)       │
└─────────────────────────────────────────┘
```

**Complete Call Flow:**

```
1. CALL COMES IN
   ↓
2. Twilio → POST /webhooks/twilio/incoming
   │
   │  Receives: CallSid, From, To, etc.
   │
   ↓
3. handle_incoming_call()
   │
   │  • Creates conversation session using ConversationalResponseTool
   │  • Maps CallSid → session_id
   │  • Generates initial greeting
   │  • Returns TwiML XML:
   │    <Response>
   │      <Start>
   │        <Stream url="wss://your-domain.com/webhooks/twilio/stream?CallSid=xxx" />
   │      </Start>
   │      <Say>Hello! How can I help you?</Say>
   │    </Response>
   │
   ↓
4. Twilio receives TwiML → Starts Media Stream
   ↓
5. Twilio → WebSocket /webhooks/twilio/stream?CallSid=xxx
   ↓
6. handle_media_stream()
   │
   │  • Accepts WebSocket connection
   │  • Looks up session using CallSid
   │  • Starts listening for audio messages
   │
   ↓
7. REAL-TIME AUDIO PROCESSING LOOP
   │
   │  When audio arrives from phone:
   │  ┌─────────────────────────────────────────┐
   │  │ A. Receive audio (μ-law PCM, 8000Hz)   │
   │  │    Buffer audio chunks (16 chunks ≈ 2s) │
   │  └──────────────┬──────────────────────────┘
   │                 ↓
   │  ┌─────────────────────────────────────────┐
   │  │ B. Convert to WAV (16000Hz)            │
   │  │    twilio_to_wav()                      │
   │  └──────────────┬──────────────────────────┘
   │                 ↓
   │  ┌─────────────────────────────────────────┐
   │  │ C. Speech-to-Text                      │
   │  │    speech_tool.transcribe()            │
   │  │    → "Hello, I need help"              │
   │  └──────────────┬──────────────────────────┘
   │                 ↓
   │  ┌─────────────────────────────────────────┐
   │  │ D. Generate AI Response                 │
   │  │    conversation_tool.generate_response()│
   │  │    → "I'd be happy to help you!"        │
   │  └──────────────┬──────────────────────────┘
   │                 ↓
   │  ┌─────────────────────────────────────────┐
   │  │ E. Text-to-Speech                       │
   │  │    tts_tool.synthesize()                │
   │  │    → Audio bytes (WAV/MP3)              │
   │  └──────────────┬──────────────────────────┘
   │                 ↓
   │  ┌─────────────────────────────────────────┐
   │  │ F. Convert back to Twilio format       │
   │  │    wav_to_twilio()                     │
   │  │    → μ-law PCM, 8000Hz                 │
   │  └──────────────┬──────────────────────────┘
   │                 ↓
   │  ┌─────────────────────────────────────────┐
   │  │ G. Send back through Media Stream      │
   │  │    In 20ms chunks (160 bytes each)     │
   │  │    Base64 encoded JSON messages        │
   │  └─────────────────────────────────────────┘
   │
   ↓
8. CALLER HEARS AI RESPONSE
   ↓
9. Loop continues (steps 7) until call ends
   ↓
10. When call ends:
    • POST /webhooks/twilio/status receives status update
    • Cleanup: Remove call from active_calls
    • Close WebSocket connection
```

**Key Components:**

1. **Audio Format Conversion** (`tools/phone/twilio_phone/audio_converter.py`)
   
   Twilio uses μ-law PCM at 8000Hz (telephony format), while OpenAI requires higher quality audio. The converter handles bidirectional conversion:
   
   **Twilio → OpenAI:**
   ```python
   # Convert μ-law PCM to WAV
   μ-law PCM (8000Hz) 
     → audioop.ulaw2lin()      # Convert to linear PCM
     → Resample to 16000Hz      # Using pydub or audioop
     → Add WAV header           # Create WAV file
     → Ready for OpenAI Whisper
   ```
   
   **OpenAI → Twilio:**
   ```python
   # Convert WAV/MP3 to μ-law PCM
   WAV/MP3 (16000Hz)
     → Load with pydub          # Handle format
     → Resample to 8000Hz       # Twilio requirement
     → Convert to mono          # Single channel
     → audioop.lin2ulaw()       # Convert to μ-law
     → Ready for Twilio
   ```

2. **TwilioPhoneTool** (`tools/phone/twilio_phone/__init__.py`)
   
   Main tool that orchestrates the phone conversation:
   
   - **`handle_incoming_call()`**: Processes webhook, creates session, returns TwiML
   - **`handle_media_stream()`**: Manages WebSocket connection, receives/sends audio
   - **`_process_phone_audio()`**: Complete pipeline (STT → Conversation → TTS)
   - **`handle_call_status()`**: Tracks call lifecycle, cleans up resources
   
   **Session Management:**
   ```python
   # Maps call to conversation
   active_calls = {
       "CA1234567890": "session_abc123"  # CallSid → session_id
   }
   
   # Stores conversation state
   session_data = {
       "session_abc123": {
           "session_id": "session_abc123",
           "customer_id": "phone_+1234567890",
           "persona": "friendly_guide",
           "history": [...],
           ...
       }
   }
   ```

3. **Audio Buffer Management**
   
   Audio is buffered before processing to improve quality:
   ```python
   # Buffer accumulates ~2 seconds of audio before processing
   if len(audio_buffer) >= 16:  # 16 chunks ≈ 2 seconds
       combined_audio = b''.join(audio_buffer)
       audio_buffer.clear()
       # Process asynchronously so we can keep receiving
       asyncio.create_task(self._process_phone_audio(...))
   ```
   
   This ensures:
   - Better transcription accuracy (more context)
   - Reduced API calls (batch processing)
   - Continuous audio reception (non-blocking)

4. **Asynchronous Processing**
   
   Audio processing runs in the background using `asyncio.create_task()`:
   - WebSocket can continue receiving new audio
   - Multiple audio segments can process simultaneously
   - No blocking of the main event loop
   - Better responsiveness

5. **Audio Chunking for Response**
   
   When sending audio back to Twilio, it's sent in small chunks:
   ```python
   # Send in 20ms chunks (160 bytes at 8000Hz)
   chunk_size = 160
   for i in range(0, len(twilio_audio), chunk_size):
       chunk = twilio_audio[i:i + chunk_size]
       # Base64 encode and send as JSON
       await websocket.send_text(json.dumps({
           "event": "media",
           "media": {"payload": base64_encoded_chunk}
       }))
   ```
   
   This provides:
   - Low latency (audio starts playing quickly)
   - Smooth playback (no audio gaps)
   - Real-time feel

6. **Integration with Existing Tools**
   
   The TwilioPhoneTool follows your tool architecture pattern:
   
   ```python
   class TwilioPhoneTool:
       def __init__(
           self,
           speech_tool: Optional[SpeechToTextTool] = None,
           tts_tool: Optional[TextToSpeechTool] = None,
           conversation_tool: Optional[ConversationalResponseTool] = None
       ):
           # Uses dependency injection
           # Reuses your existing tools
           # No modifications needed to existing code
   ```
   
   **Tool Reuse:**
   - `SpeechToTextTool`: Uses your existing OpenAI Whisper integration
   - `ConversationalResponseTool`: Uses your existing GPT conversation logic
   - `TextToSpeechTool`: Uses your existing TTS implementation
   - `ConversationManager`: Maintains conversation state and history

**Design Decisions:**

1. **Follows Your Tool Pattern**
   - Same structure as `SpeechToTextTool` and `TextToSpeechTool`
   - Dependency injection pattern
   - Modular and testable

2. **Reuses Existing Infrastructure**
   - No changes needed to existing tools
   - Leverages your conversation management
   - Uses your persona system

3. **Real-time Processing**
   - Buffers audio for better quality
   - Asynchronous processing to avoid blocking
   - Chunked audio sending for low latency

4. **Error Handling**
   - Graceful handling of STT/TTS failures
   - WebSocket disconnect handling
   - Automatic resource cleanup
   - Comprehensive logging

**File Structure:**

```
tools/phone/twilio_phone/
├── __init__.py              # TwilioPhoneTool class
│   ├── handle_incoming_call()      # Webhook handler
│   ├── handle_media_stream()       # WebSocket handler
│   ├── _process_phone_audio()      # Audio processing pipeline
│   └── handle_call_status()        # Status updates
└── audio_converter.py       # Audio format conversion
    ├── twilio_to_wav()      # Convert for OpenAI
    └── wav_to_twilio()      # Convert for Twilio
```

**API Endpoints:**

- **POST /webhooks/twilio/incoming**: Receives call webhook, returns TwiML
- **POST /webhooks/twilio/status**: Receives status updates, cleans up
- **WebSocket /webhooks/twilio/stream**: Bidirectional audio streaming

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
├── voice_processor.py     # Speech-to-text and text-to-speech facade
├── conversation_manager.py # Conversation flow management
├── personas.py            # Persona catalog describing voices and tone
├── tools/                 # Modular tool implementations
│   ├── understanding/
│   │   └── speech_to_text/
│   ├── response/
│   │   ├── conversation/
│   │   └── text_to_speech/
│   └── phone/             # Phone integration tools
│       └── twilio_phone/  # Twilio phone integration
│           ├── __init__.py
│           └── audio_converter.py
├── realtime_websocket.py  # Real-time WebSocket handler
├── serve_chat.py         # Simple server for ui/chat_ui.html
├── start_api.sh          # Helper script to launch API server
├── start_ui.sh           # Helper script to launch UI server
├── start_all.sh          # Helper script to launch both servers
├── setup_ngrok.sh         # Helper script to set up ngrok for Twilio webhooks
├── ui/                   # Next.js web client and standalone demos
│   ├── app/              # Next.js app directory
│   ├── server.js         # Custom Next.js + WebSocket proxy
│   ├── package.json      # Frontend dependencies and scripts
│   ├── chat_ui.html      # Standalone chat UI page
│   └── realtime_client.html # Realtime HTML demo client
├── config.py             # Configuration management
├── env.example           # Environment variables template (copy to .env)
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
4. **Phone Integration**: 
   - Verify Twilio credentials in `.env` file
   - Check webhook URLs are accessible (HTTPS required)
   - Verify Media Stream endpoint is working
   - Review Twilio Console logs for call details
   - Test with ngrok for local development

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
