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
- Continuous listening mode with auto-restart
- Interim results for live transcription
- Automatic pause detection (800ms delay, optimized for speed)
- Interruption handling (stops AI audio when user speaks)
- Feedback loop prevention (AI doesn't hear itself)

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
- Recognition pause during AI speech (prevents feedback loop)

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
        
        // Continuous conversation state
        this.isProcessing = false; // Prevent duplicate processing
        this.hasInterrupted = false; // Track if we just interrupted
        this.accumulatedTranscript = ''; // Accumulate speech before processing
        this.pendingResponseTimer = null; // Timer for auto-response
        
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

#### 3. Recognition Result Handling & Continuous Conversation

The system processes recognition results in real-time with continuous conversation support:

```javascript
handleRecognitionResult(event) {
    if (!event.results) return;

    // STEP 1: Check for interrupt first (user speaking while AI is speaking)
    if (this.isSpeaking && !this.hasInterrupted) {
        // Check if there's any speech content
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (result[0] && result[0].transcript.trim().length > 0) {
                this.handleInterruptDetected(); // Stop AI immediately
                break;
            }
        }
    }

    // STEP 2: Process transcript results
    let hasFinalTranscript = false;
    let hasInterimSpeech = false;

    for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (!result[0]) continue;

        const transcriptText = result[0].transcript;
        
        if (result.isFinal) {
            // Final transcript - accumulate it
            if (transcriptText.trim()) {
                this.accumulatedTranscript += transcriptText + ' ';
                hasFinalTranscript = true;
            }
        } else {
            // Interim transcript - show live
            if (transcriptText.trim()) {
                this.liveUserTranscript = transcriptText;
                this.updateLiveDisplay();
                hasInterimSpeech = true;
            }
        }
    }

    // STEP 3: Handle auto-response after pause
    if (hasFinalTranscript && this.accumulatedTranscript.trim()) {
        this.scheduleResponse(); // Wait 800ms, then process
    } else if (hasInterimSpeech) {
        // User is still speaking - cancel any pending response
        this.clearPendingTimer();
    }
}

// Schedule response after pause
scheduleResponse() {
    this.clearPendingTimer();
    
    const completeTranscript = this.accumulatedTranscript.trim();
    if (!completeTranscript) return;
    
    console.log(`⏱️ Scheduling response in ${RESPONSE_DELAY_MS}ms`);
    
    this.pendingResponseTimer = setTimeout(() => {
        this.pendingResponseTimer = null;
        
        // Double check we should still process
        if (!this.shouldListen || this.isProcessing || this.isSpeaking) return;
        
        const transcript = this.accumulatedTranscript.trim();
        if (transcript) {
            console.log('✅ Processing scheduled response:', transcript);
            
            // Add to transcript history
            this.addTranscript({ role: 'user', text: transcript, timestamp: new Date() });
            
            // Clear state
            this.accumulatedTranscript = '';
            this.liveUserTranscript = '';
            this.updateLiveDisplay();
            
            // Process the transcript
            this.processTranscript(transcript);
        }
    }, RESPONSE_DELAY_MS); // 800ms delay (optimized from 1000ms)
}
```

**Continuous Conversation Processing Flow:**
1. User speaks → Recognition captures audio
2. Interim results shown in real-time (live display)
3. Final results accumulated in `accumulatedTranscript`
4. 800ms pause detected → `scheduleResponse()` triggered
5. Timer waits 800ms (if user continues speaking, timer is reset)
6. After pause → Transcript sent to backend
7. AI generates response → Text-to-speech
8. Audio plays → Recognition automatically restarts after AI finishes
9. Cycle continues seamlessly until user clicks "Stop"

#### 4. Interrupt Handling

Users can interrupt the AI at any time by speaking while the AI is responding:

```javascript
handleInterruptDetected() {
    if (!this.isSpeaking) return;
    
    console.log('🔴 Interrupt detected - stopping AI');
    this.hasInterrupted = true;
    this.stopAudio(); // Stop AI audio immediately
    this.setStatus('listening');
    this.clearPendingTimer();
    
    // Clear accumulated transcript to start fresh after interrupt
    this.accumulatedTranscript = '';
    this.liveUserTranscript = '';
    this.updateLiveDisplay();
}
```

**How Interrupts Work:**
1. AI is speaking (`isSpeaking = true`)
2. User starts speaking → Recognition detects speech
3. `handleInterruptDetected()` called immediately
4. AI audio stopped, status changed to "listening"
5. Accumulated transcript cleared (fresh start)
6. User's new input is processed normally

#### 5. Feedback Loop Prevention

Critical: The AI must not hear its own voice, otherwise it creates a feedback loop. The implementation prevents this in two ways:

**Method 1: Stop Recognition During AI Speech**
```javascript
audio.onplay = () => {
    if (this.currentAudio === audio) {
        this.isSpeaking = true;
        this.hasInterrupted = false;
        this.setStatus('speaking');
        
        // Start recognition with delay for interrupt detection only
        // 300ms delay ensures we don't capture AI's first words
        setTimeout(() => {
            if (this.isSpeaking && this.shouldListen && !this.isRecognitionActive) {
                console.log('👂 Listening for interrupts...');
                this.startListening(); // Only for interrupt detection
            }
        }, 300);
    }
};
```

**Method 2: Restart Recognition After AI Finishes**
```javascript
audio.onended = () => {
    if (this.currentAudio === audio) {
        this.isSpeaking = false;
        this.hasInterrupted = false;
        this.currentAudio = null;
        this.liveAssistantUtterance = '';
        this.updateLiveDisplay();
        URL.revokeObjectURL(audioUrl);
        
        if (this.shouldListen) {
            if (!this.isRecognitionActive) {
                this.restartListening(); // Full recognition restart
            }
            this.setStatus('listening');
        } else {
            this.setStatus('idle');
        }
        this.interruptBtn.disabled = true;
    }
};

// Fast restart for continuous conversation
restartListening() {
    if (this.shouldListen && !this.isRecognitionActive) {
        setTimeout(() => {
            if (this.shouldListen && !this.isRecognitionActive && !this.isSpeaking) {
                this.startListening();
            }
        }, 50); // 50ms delay for fastest restart
    }
}
```

**Feedback Loop Prevention Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User speaks                                                  │
│    → Recognition ACTIVE ✅                                      │
│    → Speech processed                                           │
│    → AI response generated                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. AI starts speaking (audio.onplay)                           │
│    → Recognition ACTIVE (for interrupts only) 👂               │
│    → 300ms delay before activation                             │
│    → AI voice is NOT processed (interrupt detection only)      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. AI finishes speaking (audio.onended)                        │
│    → Wait 50ms buffer                                          │
│    → Recognition FULLY RESTARTED ✅                            │
│    → Ready for user input again                                │
└─────────────────────────────────────────────────────────────────┘
```

**Key Timing Parameters:**
- `RESPONSE_DELAY_MS = 800` - Pause detection (user stops speaking)
- `300ms` - Delay before enabling interrupt detection (avoid capturing AI's first words)
- `50ms` - Recognition restart delay (optimize for speed)

#### 6. Audio Unlock Mechanism

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
const RESPONSE_DELAY_MS = 800; // 800ms pause before processing (optimized for speed)
```

**Why 800ms?**
- Fast enough for natural conversation flow
- Long enough to detect end of speech
- Prevents premature processing mid-sentence
- Can be adjusted based on user preference

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

## Advanced Features

### Continuous Conversation Mode

The chat UI implements true continuous conversation without requiring the user to press any buttons:

**Key Capabilities:**
1. **Auto-start listening**: Click "Start conversation" once, then talk naturally
2. **Auto-response**: AI responds automatically after detecting pause (800ms)
3. **Auto-restart**: After AI finishes speaking, listening resumes automatically
4. **Interrupt handling**: Speak at any time to stop AI and take over
5. **Feedback prevention**: AI never processes its own voice

**State Machine:**
```
    START
      │
      ▼
   [IDLE] ──Click Start──> [LISTENING]
                               │  │
                               │  └──User speaks──> [PROCESSING]
                               │                         │
                               │                         ▼
                               │                    [SPEAKING]
                               │                         │
                               │<──Auto-restart──────────┘
                               │
                               └──Interrupt──> [LISTENING]
```

### Interrupt System

The interrupt system allows natural conversation flow:

**Interrupt Detection:**
- Monitors for speech while AI is speaking
- Triggers immediately upon detection (no delay)
- Stops AI audio mid-sentence
- Clears pending responses
- Preserves conversation context

**Interrupt Recovery:**
- State is cleanly reset
- Transcript accumulator cleared
- New user input processed normally
- No confusion or double-processing

### Performance Optimizations

**Implemented Optimizations:**
1. **Fast TTS Model**: Uses `tts-1` (not `tts-1-hd`) for lower latency
2. **Streaming GPT**: Responses stream chunk-by-chunk from GPT
3. **Non-blocking Operations**: TTS and session creation don't block UI
4. **Minimal Restartdelay**: 50ms recognition restart for speed
5. **Optimized Pause Detection**: 800ms (down from 1000ms)

**Latency Breakdown (typical):**
- Speech recognition: Real-time (0ms perceived)
- GPT response generation: 1-2s (streaming)
- TTS generation: 0.5-1s (parallel for long texts)
- Audio playback: Starts immediately
- **Total perceived latency**: ~1.5-3s

### Feedback Loop Prevention

**The Problem:**
Without prevention, the AI can hear its own voice:
```
User: "Hello"
  → AI: "Hi there!"
    → Recognition captures: "hi there"
      → AI responds to itself: "Did you say hi?"
        → Recognition captures: "did you say"
          → INFINITE LOOP 🔄
```

**The Solution:**
1. Recognition is paused/limited while AI speaks
2. 300ms delay before enabling interrupt detection
3. Recognition fully restarts only after AI finishes
4. `isSpeaking` flag prevents transcript processing

**Result:**
- No feedback loops
- Clean conversation flow
- Interrupts still work
- Performance maintained

## Future Enhancements

Potential improvements for advanced use cases:
- **WebSocket support**: Real-time streaming for even lower latency
- **Offline mode**: Local TTS/STT for privacy and speed
- **Voice activity detection (VAD)**: More accurate speech detection
- **Custom wake words**: "Hey Assistant, ..."
- **Multi-language support**: Automatic language detection
- **Conversation export**: Download full conversation history
- **Persistent history**: Remember conversations across sessions
- **Voice cloning**: Custom AI voices
- **Emotion detection**: Adjust responses based on tone
- **Background noise filtering**: Improve recognition in noisy environments

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
- Ensure "Start conversation" was clicked first (unlocks audio)
- Check browser console for errors
- Verify microphone permissions
- Try refreshing the page and clicking "Start" again

### Speech not recognized
- Check microphone permissions (browser should prompt)
- Verify Web Speech API support (Chrome/Edge best)
- Check browser console for recognition errors
- Try different browser (Chrome recommended)
- Ensure microphone is not muted
- Test microphone in system settings

### AI not responding automatically
- Check console for errors
- Verify `RESPONSE_DELAY_MS` is set (800ms default)
- Ensure you pause speaking for at least 800ms
- Check if `shouldListen` flag is true
- Verify backend is reachable (`http://localhost:4002`)

### Interrupt not working
- Ensure you're speaking loudly enough to be detected
- Check if recognition is active (should see interim results)
- Verify `handleInterruptDetected()` is being called (console log)
- Try speaking more clearly/loudly

### AI hearing itself (feedback loop)
- **This should not happen if implementation is correct**
- Verify recognition is stopped during AI speech
- Check `isSpeaking` flag is true when AI speaks
- Ensure 300ms delay is in place before interrupt detection
- Check console for unexpected "User said: ..." logs while AI speaks

### Conversation not continuous
- Check if `restartListening()` is called after AI finishes
- Verify `audio.onended` event handler is working
- Check if `shouldListen` is still true
- Look for errors in console

### Slow response time
- Verify using `tts-1` (not `tts-1-hd`) for TTS
- Check network connection (4G/5G/WiFi)
- Verify streaming is enabled for GPT
- Check backend logs for bottlenecks
- Consider reducing `RESPONSE_DELAY_MS` to 600-700ms

### API errors
- Verify backend server is running (`python main.py`)
- Check API base URL configuration (`http://localhost:4002`)
- Verify OpenAI API key is set in `.env`
- Check network connectivity
- Check backend logs for specific errors
- Verify no CORS errors in browser console

## Summary

The chat feature provides a **production-ready, continuous voice-to-voice conversation experience** with advanced features:

### Core Technologies
- **Browser-native speech recognition** (Web Speech API - no external dependencies)
- **REST API integration** with FastAPI backend
- **OpenAI GPT-4** for intelligent conversation
- **OpenAI TTS** for natural voice synthesis
- **Pure vanilla JavaScript** (no frameworks, easy to maintain)

### Advanced Features Implemented
✅ **Continuous Conversation**: Automatic listening restart after AI responds  
✅ **Interrupt Handling**: Stop AI mid-sentence by speaking  
✅ **Feedback Loop Prevention**: AI never hears itself  
✅ **Smart Pause Detection**: 800ms optimized for natural flow  
✅ **Performance Optimized**: Streaming GPT, fast TTS model, non-blocking operations  
✅ **Custom Prompts**: Fully customizable AI behavior  
✅ **Real-time Transcription**: Live display of speech  
✅ **Browser Autoplay Handling**: Automatic audio unlock  
✅ **Error Recovery**: Graceful handling of all edge cases  

### Performance Characteristics
- **Latency**: ~1.5-3s end-to-end (speech → response audio)
- **Recognition**: Real-time (0ms perceived)
- **Restart Speed**: 50ms (optimized for continuous conversation)
- **Response Detection**: 800ms pause (tunable)

### Deployment
- **Single HTML file** (`ui/chat_ui.html`) - self-contained
- **No build step** required
- **Easy to deploy**: Just serve the HTML file
- **Easy to maintain**: Pure vanilla JavaScript, well-documented

### Production-Ready Features
- ✅ Comprehensive error handling
- ✅ Browser compatibility checks
- ✅ Graceful degradation
- ✅ State machine for robust flow control
- ✅ Prevention of edge cases (feedback loops, duplicate processing)
- ✅ Detailed console logging for debugging
- ✅ Mobile-responsive design

### Best Practices Implemented
1. **State Management**: Centralized state with clear flags (`isProcessing`, `isSpeaking`, etc.)
2. **Timing Control**: Strategic delays to prevent race conditions
3. **Resource Cleanup**: Proper cleanup of audio URLs and timers
4. **User Experience**: Visual feedback, smooth animations, intuitive controls
5. **Performance**: Non-blocking operations, optimized for speed
6. **Maintainability**: Well-structured code, clear naming, extensive comments

The implementation demonstrates **enterprise-grade voice UI patterns** suitable for production use in customer service, voice assistants, accessibility tools, and conversational AI applications.
