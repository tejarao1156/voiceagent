# OpenAI Realtime Voice Chat - Next.js App

A minimal full-stack Next.js + TypeScript web app that lets you talk to OpenAI's Realtime API using your microphone and hear the model reply with speech.

## Features

- 🎙️ **Voice Input**: Use your microphone to talk to OpenAI's Realtime API
- 🔊 **Voice Output**: Hear the AI assistant respond with speech
- 💬 **Live Transcripts**: See real-time transcripts of both user and assistant messages
- 📊 **Status Indicators**: Visual connection status (idle/connecting/connected/stopped)

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy `.env.local.example` to `.env.local`:

```bash
cp .env.local.example .env.local
```

Edit `.env.local` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

1. Click **"Start Conversation 🎙️"** button
2. Grant microphone permission when prompted
3. Start speaking - the AI will respond with voice
4. See live transcripts in the conversation panel
5. Click **"Stop ⏹️"** to end the conversation

## Project Structure

```
app/
  ├── page.tsx              # Main page with UI and WebSocket logic
  ├── layout.tsx            # Root layout
  ├── globals.css            # Global styles with Tailwind
  └── api/
      └── session/
          └── route.ts       # API route to create OpenAI Realtime session
```

## How It Works

1. **Session Creation**: Frontend calls `/api/session` which creates a session with OpenAI's Realtime API
2. **WebSocket Connection**: Frontend connects directly to OpenAI's WebSocket endpoint using the session ID
3. **Audio Capture**: Browser captures microphone audio and converts it to PCM16 format
4. **Audio Streaming**: Audio chunks are sent to OpenAI via WebSocket
5. **Audio Playback**: Assistant's audio responses are decoded and played through browser audio
6. **Transcripts**: Both user and assistant transcripts are displayed in real-time

## Technologies

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **WebSocket API** - Real-time bidirectional communication
- **Web Audio API** - Audio capture and playback
- **OpenAI Realtime API** - Voice conversation AI

## Notes

- The OpenAI Realtime API requires authentication via session ID (created server-side)
- Audio format is PCM16 at 24kHz sample rate
- The app uses server-side VAD (Voice Activity Detection) for turn detection
- Make sure to use HTTPS in production for microphone access

