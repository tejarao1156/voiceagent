# SMS Outgoing Flow

Handles outbound SMS messages through campaigns or direct sends.

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Dashboard
    participant API as api_general.py
    participant Worker as CampaignWorker
    participant Store as MongoDBCampaignStore
    participant Twilio
    participant Recipient

    User->>UI: Create SMS Campaign
    UI->>API: POST /api/campaigns
    Note over API: type: "sms", config: {messageBody}
    API->>Store: Create campaign + items
    
    User->>UI: Start Campaign
    UI->>API: POST /api/campaigns/{id}/start
    
    loop Batch Processing
        Worker->>Store: acquire_pending_items(10)
        Store-->>Worker: Locked items
        
        par Parallel SMS
            Worker->>Twilio: client.messages.create()
            Worker->>Twilio: client.messages.create()
            Worker->>Twilio: ...
        end
        
        Twilio->>Recipient: Delivers SMS
        Worker->>Store: Update status → sent
        Worker->>Store: Log to campaign_executions
        Worker->>Store: Save to messages (conversation)
    end
```

## Key Files

| File | Purpose |
|------|---------|
| [campaign_worker.py](../utils/campaign_worker.py) | `_send_sms()` method |
| [mongodb_campaign_store.py](../databases/mongodb_campaign_store.py) | Campaign storage |
| [mongodb_message_store.py](../databases/mongodb_message_store.py) | Conversation history |

## Database Collections

| Collection | Data Stored |
|------------|-------------|
| `campaign_items` | phone_number, status |
| `campaign_executions` | message_sid, status, from/to |
| `messages` | Outbound message stored in conversation |

## Message Body Template

The `messageBody` in campaign config is sent as-is to all recipients. Future enhancement: variable substitution (e.g., {{name}}).
