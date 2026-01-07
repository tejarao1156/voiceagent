# AI Chat Flow

Browser-based real-time voice chat with AI, using microphone input and audio playback.

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant WS as WebSocket
    participant API as api_general.py
    participant STT as Speech-to-Text
    participant LLM
    participant TTS as Text-to-Speech

    User->>Browser: Click "Start Chat"
    Browser->>WS: Connect /ws/ai-chat
    Browser->>Browser: Request microphone access
    
    loop Conversation
        User->>Browser: Speaks into microphone
        Browser->>WS: Audio chunks (base64)
        WS->>STT: Convert to text
        
        Note over STT: Silence detection (1.5s)
        STT-->>WS: Transcript
        
        WS->>LLM: Process with context
        LLM-->>WS: Response (streaming)
        
        WS->>TTS: Convert to audio
        TTS-->>WS: Audio chunks
        WS->>Browser: Audio (base64)
        Browser->>User: Plays audio response
    end
    
    User->>Browser: Click "End Chat"
    Browser->>WS: Close connection
```

## Inactivity Management

```mermaid
flowchart LR
    A[User Silent] --> B{10s passed?}
    B -->|Yes| C[Send Reminder]
    C --> D{3 reminders?}
    D -->|Yes| E[End Session]
    D -->|No| A
    B -->|User Speaks| F[Reset Timer]
```

## Key Files

| File | Purpose |
|------|---------|
| [api_general.py](../api_general.py) | `/ws/ai-chat` WebSocket endpoint |
| [stt_provider_factory.py](../utils/stt_provider_factory.py) | Speech-to-Text |
| [tts_provider_factory.py](../utils/tts_provider_factory.py) | Text-to-Speech |

## Frontend Components

| File | Purpose |
|------|---------|
| `AIChatView.tsx` | Main chat UI component |
| Audio handling | Web Audio API for mic capture & playback |

## WebSocket Message Types

### Client → Server
```json
{"type": "audio", "data": "<base64 audio>"}
{"type": "config", "stt_model": "...", "tts_voice": "..."}
{"type": "end"}
```

### Server → Client
```json
{"type": "transcript", "text": "Hello"}
{"type": "audio", "data": "<base64 audio>"}
{"type": "inactivity_reminder", "count": 1}
{"type": "inactivity_end"}
```

## Audio Format

- **Input**: Raw PCM, 16kHz, mono
- **Output**: Varies by TTS provider (typically mp3 or pcm)
