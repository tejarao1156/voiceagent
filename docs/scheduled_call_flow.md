# Scheduled Call Flow

This document outlines the end-to-end flow of a scheduled call in the Voice Agent system.

## 1. Scheduling (API/UI)
*   **Endpoint**: `POST /api/scheduled-calls`
*   **Input**:
    *   `toPhoneNumbers`: List of recipients.
    *   `promptId`: ID of the prompt to use.
    *   `scheduledDateTime`: When to make the call.
*   **Process**:
    1.  Validates the request.
    2.  Fetches the **Prompt** (including `content` and `introduction`) from MongoDB.
    3.  Creates a record in the `scheduled_calls` collection with status `pending`.
    4.  Stores the prompt content *inside* the scheduled call record (snapshot).

## 2. Background Processing (Worker)
*   **Component**: `ScheduledCallWorker` (in `utils/scheduled_call_worker.py`)
*   **Loop**: Runs every 60 seconds.
*   **Process**:
    1.  Queries MongoDB for calls where `scheduledDateTime <= now` and `status == 'pending'`.
    2.  Updates status to `in_progress`.
    3.  Iterates through `toPhoneNumbers`.
    4.  **Initiates Call**: Uses Twilio API (`client.calls.create`) to dial the recipient.
    5.  **Webhook URL**: Sets the callback URL to:
        ```
        /webhooks/twilio/incoming?scheduled_call_id={ID}&is_scheduled=true
        ```
    6.  Logs the call initiation to `calllogs` collection.

## 3. Call Connection (Twilio & Webhook)
*   **Action**: Recipient answers the phone.
*   **Twilio Request**: Twilio sends a POST request to the Webhook URL.
*   **Webhook Handler** (`api_general.py` -> `twilio_incoming_call`):
    1.  Extracts `scheduled_call_id` from query params.
    2.  Fetches the Scheduled Call from DB to validate.
    3.  **Response**: Returns TwiML to connect to the Media Stream:
        ```xml
        <Response>
            <Connect>
                <Stream url="wss://.../webhooks/twilio/stream">
                    <Parameter name="ScheduledCallId" value="{ID}" />
                    <Parameter name="IsOutbound" value="true" />
                </Stream>
            </Connect>
        </Response>
        ```

## 4. Real-time Stream (WebSocket)
*   **Component**: `TwilioStreamHandler` (in `tools/phone/twilio_phone_stream.py`)
*   **Process**:
    1.  Accepts WebSocket connection.
    2.  **Start Event**: Receives `start` event with Custom Parameters.
    3.  **Config Loading**:
        *   Reads `ScheduledCallId` from parameters.
        *   Fetches the Scheduled Call from MongoDB.
        *   Constructs a **Virtual Agent Configuration** using the stored Prompt and Introduction.
    4.  **Greeting**:
        *   Sends the `introduction` (Greeting) to TTS.
        *   Streams audio to the user ("Hello! I am calling regarding...").
    5.  **Conversation**:
        *   Listens for user audio (VAD).
        *   Transcribes (STT).
        *   Generates AI response (LLM) using the System Prompt.
        *   Streams response (TTS).

## 5. Completion
*   **Worker**: Updates scheduled call status to `completed` after all calls are initiated.
*   **Call Log**: Updates `calllogs` with duration and status when call ends.
