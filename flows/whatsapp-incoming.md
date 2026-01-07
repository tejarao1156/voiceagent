# WhatsApp Incoming Flow

Handles incoming WhatsApp messages via Twilio webhooks.

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Twilio
    participant API as api_general.py
    participant Agent as MessagingAgent
    participant LLM
    participant DB as MongoDB

    User->>Twilio: Sends WhatsApp message
    Twilio->>API: POST /webhooks/twilio/whatsapp
    API->>DB: Identify agent by To number
    API->>DB: Get conversation history
    API->>Agent: Process message with context
    Agent->>LLM: Generate response
    LLM-->>Agent: AI response
    Agent->>Twilio: Send WhatsApp reply
    Twilio->>User: Delivers response
    API->>DB: Save messages
```

## Key Files

| File | Purpose |
|------|---------|
| [api_general.py](../api_general.py) | `/webhooks/twilio/whatsapp` - Webhook handler |
| [mongodb_message_store.py](../databases/mongodb_message_store.py) | Conversation storage |

## Database Collections

| Collection | Data Stored |
|------------|-------------|
| `messages` | from, to, body, channel (whatsapp), timestamp |

## WhatsApp Format

Numbers are prefixed with `whatsapp:` when communicating with Twilio:
- From: `whatsapp:+15551234567`
- To: `whatsapp:+15559876543`
