# Call Flow Testing API Implementation Plan

## Overview
Creating comprehensive testing APIs for each step of the incoming call flow, following DEVELOPMENT_INSTRUCTIONS.md principles.

## Call Flow Steps (What Happens During a Call)

### 1. **Incoming Call** 
- Twilio receives call → POST `/webhooks/twilio/incoming`
- Creates session, returns TwiML to start media stream

### 2. **Media Stream** 
- WebSocket connection → `/webhooks/twilio/stream`
- Real-time bidirectional audio

### 3. **Audio Reception** 
- Receive μ-law PCM audio from Twilio (8kHz)
- Buffer audio chunks

### 4. **Voice Activity Detection (VAD)**
- Detect when user is speaking
- Buffer speech until silence detected

### 5. **Speech-to-Text (STT)**
- Convert audio to WAV format
- Send to OpenAI Whisper
- Get transcribed text

### 6. **LLM Processing**
- Send user text + conversation history to GPT
- Get AI response text

### 7. **Text-to-Speech (TTS)**
- Convert AI response to audio
- Use OpenAI TTS

### 8. **Audio Streaming**
- Convert audio to μ-law PCM
- Stream back to Twilio
- User hears response

### 9. **Interrupt Detection**
- Detect if user speaks while AI is talking
- Stop AI, process new question

### 10. **Call End**
- Clean up resources
- Save transcript to MongoDB

---

## Testing APIs to Create

Following the principle: **Each step should be testable independently**

### Category 1: Audio Processing APIs
Test audio conversion and VAD without full call

1. **POST `/api/test/audio/convert-to-wav`**
   - Input: μ-law PCM audio (base64)
   - Output: WAV audio (base64)
   - Tests: Audio format conversion

2. **POST `/api/test/audio/convert-to-mulaw`**
   - Input: WAV/MP3 audio (base64)
   - Output: μ-law PCM (base64)
   - Tests: Reverse audio conversion

3. **POST `/api/test/audio/vad-detect`**
   - Input: Audio (base64)
   - Output: Speech detected (yes/no), confidence
   - Tests: Voice activity detection

### Category 2: STT Testing APIs
Test speech-to-text independently

4. **POST `/api/test/stt/transcribe`**
   - Input: Audio file or base64
   - Output: Transcribed text
   - Tests: STT without call context

5. **POST `/api/test/stt/transcribe-with-model`**
   - Input: Audio + model name
   - Output: Transcribed text
   - Tests: Different STT models

### Category 3: LLM Testing APIs
Test conversation logic independently

6. **POST `/api/test/llm/generate-response`**
   - Input: User text + conversation history
   - Output: AI response
   - Tests: LLM without audio

7. **POST `/api/test/llm/generate-with-prompt`**
   - Input: User text + custom system prompt
   - Output: AI response
   - Tests: Custom prompts

### Category 4: TTS Testing APIs
Test text-to-speech independently

8. **POST `/api/test/tts/synthesize`**
   - Input: Text
   - Output: Audio file (MP3/WAV)
   - Tests: TTS without call context

9. **POST `/api/test/tts/synthesize-with-voice`**
   - Input: Text + voice name
   - Output: Audio file
   - Tests: Different TTS voices

### Category 5: End-to-End Flow Testing
Test complete pipeline without actual call

10. **POST `/api/test/flow/audio-to-text-to-response`**
    - Input: Audio file
    - Output: {transcript, ai_response, response_audio}
    - Tests: STT → LLM → TTS pipeline

11. **POST `/api/test/flow/simulate-conversation-turn`**
    - Input: Audio + conversation_id
    - Output: Complete turn (transcript, response, audio)
    - Tests: Full conversation turn with history

### Category 6: Call Flow Monitoring (Already Exists)
Keep existing call flow testing APIs

12. **GET `/api/test/call-flow/settings`** ✅ (Keep)
13. **GET `/api/test/call-flow/active-calls`** ✅ (Keep)
14. **POST `/api/test/call-flow/simulate-interrupt`** ✅ (Keep)
15. **GET `/api/test/call-flow/diagnostics`** ✅ (Keep)
16. **GET `/api/test/call-flow/conversation-history/{call_sid}`** ✅ (Keep)

---

## Implementation Strategy

### Phase 1: Audio Processing APIs (1-3)
- Reuse existing audio conversion code
- Expose VAD functionality
- No new dependencies

### Phase 2: STT APIs (4-5)
- Reuse `SpeechToTextTool`
- Add model selection
- Return detailed results

### Phase 3: LLM APIs (6-7)
- Reuse `ConversationalResponseTool`
- Allow custom prompts
- Return full context

### Phase 4: TTS APIs (8-9)
- Reuse `TextToSpeechTool`
- Add voice selection
- Return audio files

### Phase 5: End-to-End APIs (10-11)
- Combine all tools
- Simulate full conversation
- Maintain state

---

## Following DEVELOPMENT_INSTRUCTIONS.md

✅ **Minimal Changes**: Only add new endpoints, don't modify existing code
✅ **Reuse Existing Code**: Use existing tools (STT, TTS, LLM, audio conversion)
✅ **Test Everything**: Each API is self-testing
✅ **Maintain Existing Flow**: Don't break current call handling
✅ **No Dummy Data**: All APIs use real tools
✅ **Edge Cases**: Handle errors, invalid input, missing data

---

## Benefits

1. **Independent Testing**: Test each component separately
2. **Debugging**: Identify which step is failing
3. **Development**: Build features without making calls
4. **Documentation**: APIs serve as examples
5. **Integration**: Easy to integrate with UI/tests

---

## Next Steps

1. ✅ Remove unwanted cleanup endpoints
2. 🔄 Implement Audio Processing APIs
3. 🔄 Implement STT APIs
4. 🔄 Implement LLM APIs
5. 🔄 Implement TTS APIs
6. 🔄 Implement End-to-End APIs
7. ✅ Keep existing call flow APIs
8. 📝 Document all APIs in Swagger
9. 🧪 Test each API
10. ✅ Verify no existing flows broken
