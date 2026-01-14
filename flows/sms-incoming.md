# SMS Incoming Flow

Handles incoming SMS messages via Twilio webhooks, stores conversation history, and generates AI responses.

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Twilio
    participant API as api_general.py
    participant Agent as MessagingAgent
    participant LLM
    participant DB as MongoDB

    User->>Twilio: Sends SMS
    Twilio->>API: POST /webhooks/twilio/sms
    API->>DB: Identify agent by To number
    API->>DB: Get conversation history
    API->>Agent: Process message with context
    Agent->>LLM: Generate response
    LLM-->>Agent: AI response
    Agent->>Twilio: Send reply SMS
    Twilio->>User: Delivers response
    API->>DB: Save messages to conversation
```

## Key Files

| File | Purpose |
|------|---------|
| [api_general.py](../api_general.py) | `/webhooks/twilio/sms` - Webhook handler |
| [mongodb_message_store.py](../databases/mongodb_message_store.py) | Conversation storage |

## Database Collections

| Collection | Data Stored |
|------------|-------------|
| `messages` | from, to, body, channel (sms), timestamp, direction |
| `conversations` | Grouped messages by phone number pair |

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/webhooks/twilio/sms` | Twilio calls this for incoming SMS |
