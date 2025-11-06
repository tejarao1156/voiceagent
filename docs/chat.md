> **⚠️ IMPORTANT: DO NOT MODIFY THIS FILE**
> 
> This documentation file should **NOT be changed** unless explicitly requested by the user.
> Only update this file when the user specifically asks you to do so.
> 
> If you need to update the documentation, ask the user first or create a separate documentation file.

---

# Chat Feature Implementation

## Overview

The Chat feature is a speech-to-speech voice agent interface that enables real-time voice conversations with an AI assistant. Users can speak naturally, and the AI responds with synthesized speech. The implementation consists of a single-page HTML application (`ui/chat_ui.html`) that integrates with the FastAPI backend through REST endpoints.

## Architecture

```
┌─────────────────────┐
│   Browser Client    │
│  (chat_ui.html)     │
│                     │
│  ┌───────────────┐ │
│  │ Web Speech API │ │◄── Speech Recognition (Browser)
│  └───────────────┘ │
│                     │
│  ┌───────────────┐ │
│  │  HTML5 Audio  │ │◄── Audio Playback (Browser)
│  └───────────────┘ │
└──────────┬──────────┘
           │ HTTP REST API
           ▼
┌─────────────────────┐
│   FastAPI Backend   │
│                     │
│  ┌───────────────┐ │
│  │ Conversation  │ │◄── Session Management
│  │   Manager     │ │
│  └───────────────┘ │
│                     │
│  ┌───────────────┐ │
│  │ Text-to-Speech│ │◄── OpenAI TTS API
│  └───────────────┘ │
└─────────────────────┘
```

## Key Features

### 1. Real-time Speech Recognition
- Uses browser's native Web Speech API
- Continuous listening mode
- Interim results for live transcription
- Automatic pause detection (1 second delay)
- Interruption handling (stops AI audio when user speaks)

### 2. Visual Status Indicators
- **Idle**: Gray dot - Waiting to start
- **Listening**: Blue pulsing dot - Actively listening
- **Processing**: Yellow pulsing dot - Generating response
- **Speaking**: Green pulsing dot - Playing audio response

### 3. Live Transcription Display
- Real-time display of what you're saying (interim results)
- Real-time display of what the AI is saying (before audio plays)
- Conversation history with timestamps
- Clean, simple styling

### 4. Custom Prompt System
- **Textarea input** for entering custom prompts
- Default prompt provided: "You are a friendly and helpful voice agent..."
- Users can customize AI behavior and personality through text prompts
- Prompt is sent to backend with each conversation request
- No predefined personas - fully customizable per user needs
- Example prompts:
  - "You are a helpful customer service representative"
  - "You are a knowledgeable tech support agent"
  - "You are a friendly restaurant host"

### 5. Audio Playback Management
- Browser autoplay unlock mechanism
- Automatic audio playback
- Interruption support (user can speak over AI)
- Error handling and retry logic

## UI Implementation Details

### File Structure
- **Location**: `ui/chat_ui.html`
- **Type**: Single-page HTML application (no build step required)
- **Access**: `http://localhost:4002/chat` (served by FastAPI)

### Technology Stack
- **Frontend**: Vanilla JavaScript (ES6+)
- **Styling**: CSS3 with modern features (gradients, backdrop-filter, animations)
- **Speech Recognition**: Web Speech API (`SpeechRecognition` or `webkitSpeechRecognition`)
- **Audio Playback**: HTML5 Audio API
- **API Communication**: Fetch API

### Core Components

#### 1. SpeechToSpeechAgent Class

The main JavaScript class that orchestrates the entire chat experience.

```javascript
class SpeechToSpeechAgent {
    constructor() {
        // State management
        this.status = 'idle';
        this.sessionId = null;
        this.sessionData = null;
        this.selectedPrompt = DEFAULT_PROMPT; // Default prompt text
        this.sessionPrompt = null;
        this.transcripts = [];
        this.recognition = null;
        this.isRecognitionActive = false;
        this.shouldListen = false;
        this.currentAudio = null;
        this.isSpeaking = false;
        this.audioUnlocked = false; // For browser autoplay unlock
        
        // Initialize components
        this.initializeElements();
        this.checkBrowserSupport();
        this.setupEventListeners();
    }
}
```

#### 2. Speech Recognition Setup

Uses the browser's native Web Speech API for speech-to-text:

```javascript
initializeRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = true;      // Keep listening
    recognition.interimResults = true;  // Show partial results
    recognition.lang = 'en-US';
    
    recognition.onresult = (event) => this.handleRecognitionResult(event);
    recognition.onstart = () => { /* Handle start */ };
    recognition.onend = () => { /* Handle end and restart */ };
    recognition.onerror = (event) => { /* Handle errors */ };
    
    this.recognition = recognition;
}
```

**Key Recognition Features:**
- **Continuous Mode**: Keeps listening after each utterance
- **Interim Results**: Shows live transcription as you speak
- **Auto-restart**: Automatically restarts if recognition ends unexpectedly
- **Error Handling**: Gracefully handles recognition errors

#### 3. Recognition Result Handling

The system processes recognition results in real-time:

```javascript
handleRecognitionResult(event) {
    // Process interim results (live display)
    for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result[0]) {
            const transcriptText = result[0].transcript;
            
            if (result.isFinal) {
                // Final result - add to accumulated transcript
                this.accumulatedTranscript += transcriptText + ' ';
            } else {
                // Interim result - show live
                this.liveUserTranscript = transcriptText;
                this.updateLiveDisplay();
            }
        }
    }
    
    // Wait 1 second after final result, then process
    if (hasFinalTranscript) {
        this.pendingResponseTimer = setTimeout(() => {
            this.processTranscript(completeTranscript);
        }, RESPONSE_DELAY_MS); // 1000ms delay
    }
}
```

**Processing Flow:**
1. User speaks → Recognition captures audio
2. Interim results shown in real-time
3. Final results accumulated
4. 1-second pause detected → Process transcript
5. Send to backend → Get AI response
6. Convert response to speech → Play audio

#### 4. Audio Unlock Mechanism

Browsers block autoplay until user interaction. The chat UI implements an unlock mechanism:

```javascript
async unlockAudio() {
    // Unlock audio playback by playing a silent audio on user interaction
    if (!this.audioUnlocked) {
        try {
            const silentAudio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=');
            silentAudio.volume = 0;
            await silentAudio.play();
            silentAudio.pause();
            this.audioUnlocked = true;
        } catch (e) {
            console.warn('Could not unlock audio:', e);
        }
    }
}
```

**How it works:**
1. User clicks "Start conversation" (user interaction)
2. `unlockAudio()` is called
3. Plays a silent audio file (volume = 0)
4. Browser registers user interaction
5. All subsequent audio can play automatically

**Called in:**
- `startConversation()` - When user starts a session
- `speakResponse()` - Before playing any audio (fallback)

#### 5. Text-to-Speech Integration

The UI fetches audio from the backend TTS API:

```javascript
async speakResponse(text) {
    // Ensure audio is unlocked
    if (!this.audioUnlocked) {
        await this.unlockAudio();
    }
    
    // Fetch TTS audio from backend
    const response = await fetch(`${API_BASE_URL}/voice/text-to-speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    });
    
    const data = await response.json();
    
    // Decode base64 audio
    const audioBytes = Uint8Array.from(atob(data.audio_base64), c => c.charCodeAt(0));
    const audioFormat = data.format || 'wav';
    const mimeType = audioFormat === 'mp3' ? 'audio/mpeg' : 'audio/wav';
    
    // Create audio element and play
    const audioBlob = new Blob([audioBytes], { type: mimeType });
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    
    // Play audio (default playback rate)
    await audio.play();
}
```

**Audio Handling:**
- Supports WAV and MP3 formats
- Base64 decoding of audio data
- Blob URL creation for playback
- Standard playback rate (no persona-specific adjustments)
- Automatic cleanup of Blob URLs

#### 6. Conversation Flow

Complete conversation processing flow:

```javascript
async processTranscript(transcript) {
    // 1. Update prompt from textarea
    this.updatePrompt();
    
    // 2. Ensure session exists
    const sessionId = await this.ensureSession();
    
    // 3. Send transcript to backend with prompt
    const response = await fetch(`${API_BASE_URL}/conversation/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: transcript,
            session_id: sessionId,
            prompt: this.selectedPrompt
        })
    });
    
    const data = await response.json();
    
    // 4. Extract response text
    let assistantText = data.response.trim();
    
    // 5. Add to conversation history
    this.addTranscript({
        role: 'assistant',
        text: assistantText,
        timestamp: new Date()
    });
    
    // 6. Display live utterance
    this.liveAssistantUtterance = assistantText;
    this.updateLiveDisplay();
    
    // 7. Convert to speech and play
    await this.speakResponse(assistantText);
}
```

## Backend API Integration

### Endpoints Used

#### 1. POST `/conversation/start`
**Purpose**: Create a new conversation session

**Request:**
```javascript
POST /conversation/start?prompt=You%20are%20a%20helpful%20assistant
```

**Response:**
```json
{
    "session_id": "mem_123456789",
    "session_data": {
        "state": "greeting",
        "customer_id": null,
        "conversation_history": [],
        "prompt": "You are a helpful assistant"
    },
    "message": "Conversation started successfully",
    "prompt": "You are a helpful assistant"
}
```

#### 2. POST `/conversation/process`
**Purpose**: Process user input and generate AI response

**Request:**
```json
{
    "text": "Hello, how are you?",
    "session_id": "mem_123456789",
    "prompt": "You are a friendly and helpful voice agent."
}
```

**Response:**
```json
{
    "response": "I'm doing great, thank you! How can I help you today?",
    "session_data": {
        "state": "active",
        "conversation_history": [...]
    },
    "prompt": "You are a friendly and helpful voice agent."
}
```

#### 3. POST `/voice/text-to-speech`
**Purpose**: Convert text to speech audio

**Request:**
```json
{
    "text": "Hello, how can I help you?"
}
```

**Response:**
```json
{
    "success": true,
    "audio_base64": "UklGRigAAABXQVZFZm10IBAAAAAB...",
    "text": "Hello, how can I help you?",
    "format": "mp3",
    "voice": "nova",
    "model": "tts-1-hd"
}
```

## UI/UX Features

### Visual Design
- **Modern gradient background** (dark theme)
- **Glassmorphism effect** (backdrop-filter blur)
- **Smooth animations** (pulsing status indicators)
- **Responsive layout** (works on desktop and mobile)
- **Color-coded status** (idle/listening/processing/speaking)

### User Interactions
- **Start Conversation**: Begins listening and unlocks audio
- **Stop Conversation**: Stops listening and ends session
- **Interrupt**: Stops AI audio when user starts speaking
- **Custom Prompt Input**: Enter text to customize AI behavior and personality
- **Real-time Feedback**: Live transcription and status updates

### Error Handling
- **Browser compatibility checks**: Warns if Web Speech API unavailable
- **Audio playback errors**: Graceful fallback and retry
- **API errors**: Clear error messages to user
- **Network errors**: Automatic retry where appropriate

## Browser Compatibility

### Supported Browsers
- **Chrome/Edge**: Full support (Web Speech API)
- **Safari**: Partial support (webkitSpeechRecognition)
- **Firefox**: Not supported (no Web Speech API)

### Requirements
- Modern browser with Web Speech API support
- Microphone access permission
- Audio playback capability
- JavaScript enabled

### Browser-Specific Notes
- **Chrome**: Best support, continuous recognition works well
- **Safari**: Uses `webkitSpeechRecognition`, may have limitations
- **Firefox**: Currently not supported (no native speech recognition)

## Technical Implementation Details

### State Management
The chat UI maintains state for:
- Current conversation session
- Recognition status (active/inactive)
- Audio playback status
- Conversation history
- Custom prompt text
- UI status (idle/listening/processing/speaking)

### Session Management
- Sessions are created on-demand
- Session ID is stored client-side
- Session data synced with backend
- In-memory sessions if database unavailable

### Audio Format Handling
- Backend returns audio as base64-encoded MP3 or WAV
- Client decodes base64 to Uint8Array
- Creates Blob with appropriate MIME type
- Uses Blob URL for Audio element
- Cleans up Blob URLs after playback

### Prompt Management
The chat UI uses a textarea for custom prompts:

```javascript
const DEFAULT_PROMPT = "You are a friendly and helpful voice agent. Your role is to engage in natural, helpful conversations with users, provide useful information and assistance, and be conversational and natural.";

// Update prompt from textarea
updatePrompt() {
    this.selectedPrompt = this.promptInput.value.trim() || DEFAULT_PROMPT;
}
```

**Prompt Features:**
- Default prompt provided on page load
- Users can edit or clear the prompt
- Prompt is sent with each conversation request
- Empty prompt falls back to default
- Prompt changes reset the session

## Usage Flow

1. **User opens chat UI** → `http://localhost:4002/chat`
2. **Enters custom prompt** (optional, default prompt provided)
3. **Clicks "Start conversation"**:
   - Unlocks audio playback
   - Creates session via API
   - Starts speech recognition
   - Begins listening
4. **User speaks**:
   - Recognition captures audio
   - Live transcription displayed
   - Final transcript sent after 1-second pause
5. **AI processes**:
   - Transcript sent to `/conversation/process`
   - GPT generates response
   - Response text displayed
6. **AI responds**:
   - Text sent to `/voice/text-to-speech`
   - Audio generated
   - Audio played to user
7. **Cycle continues** until user stops conversation

## Configuration

### API Base URL
```javascript
const API_BASE_URL = 'http://localhost:4002';
```

### Response Delay
```javascript
const RESPONSE_DELAY_MS = 1000; // 1 second pause before processing
```

### Prompt Configuration
- Default prompt: "You are a friendly and helpful voice agent..."
- Users can customize the prompt text in the textarea
- Prompt is sent as a query parameter or in request body
- Backend uses prompt to customize AI behavior

## Error Scenarios Handled

1. **Browser doesn't support Web Speech API**
   - Shows warning message
   - Disables start button

2. **Microphone permission denied**
   - Recognition error handler catches it
   - Shows error message to user

3. **Audio playback blocked**
   - Unlock mechanism attempts to fix
   - Shows helpful error message
   - Suggests clicking "Start conversation"

4. **Network errors**
   - API calls fail gracefully
   - Error messages shown
   - Fallback responses generated

5. **Session creation fails**
   - Uses in-memory session as fallback
   - Continues conversation normally

## Future Enhancements

Potential improvements:
- WebSocket support for lower latency
- Offline mode with local TTS
- Voice activity detection (VAD)
- Custom wake words
- Multi-language support
- Conversation export
- History persistence
- Voice cloning options

## Files and Dependencies

### Frontend Files
- `ui/chat_ui.html` - Complete chat UI implementation

### Backend Endpoints
- `POST /conversation/start?prompt=...` - Session creation with prompt
- `POST /conversation/process` - Conversation processing with prompt
- `POST /voice/text-to-speech` - Audio generation

### Dependencies
- **Browser APIs**: Web Speech API, HTML5 Audio API, Fetch API
- **Backend**: FastAPI, OpenAI TTS, OpenAI GPT
- **No external libraries**: Pure vanilla JavaScript

## Testing

To test the chat feature:

1. **Start the backend server**:
   ```bash
   python main.py
   ```

2. **Open the chat UI**:
   - Navigate to `http://localhost:4002/chat`
   - Or open `ui/chat_ui.html` directly in browser

3. **Test speech recognition**:
   - Click "Start conversation"
   - Speak into microphone
   - Verify live transcription appears

4. **Test AI response**:
   - Wait for AI to generate response
   - Verify audio plays
   - Check conversation history

5. **Test interruptions**:
   - Start speaking while AI is responding
   - Verify AI audio stops
   - Verify recognition continues

## Troubleshooting

### Audio not playing
- Check browser autoplay settings
- Ensure "Start conversation" was clicked first
- Check browser console for errors
- Verify microphone permissions

### Speech not recognized
- Check microphone permissions
- Verify Web Speech API support
- Check browser console for errors
- Try different browser (Chrome recommended)

### API errors
- Verify backend server is running
- Check API base URL configuration
- Verify OpenAI API key is set
- Check network connectivity

## Summary

The chat feature provides a complete voice-to-voice conversation experience using:
- Browser-native speech recognition (no external dependencies)
- REST API integration with FastAPI backend
- OpenAI TTS for natural voice synthesis
- Modern, responsive UI with real-time feedback
- Robust error handling and browser compatibility checks

The implementation is self-contained in a single HTML file, making it easy to deploy and maintain.
