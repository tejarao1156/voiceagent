# WhatsApp Outgoing Flow

Handles outbound WhatsApp messages through campaigns.

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

    User->>UI: Create WhatsApp Campaign
    UI->>API: POST /api/campaigns
    Note over API: type: "whatsapp", config: {messageBody}
    API->>Store: Create campaign + items
    
    User->>UI: Start Campaign
    UI->>API: POST /api/campaigns/{id}/start
    
    loop Batch Processing
        Worker->>Store: acquire_pending_items(10)
        Store-->>Worker: Locked items
        
        par Parallel WhatsApp
            Worker->>Twilio: messages.create(whatsapp:+1...)
            Worker->>Twilio: messages.create(whatsapp:+1...)
        end
        
        Twilio->>Recipient: Delivers WhatsApp
        Worker->>Store: Update status
        Worker->>Store: Log to campaign_executions
    end
```

## Key Files

| File | Purpose |
|------|---------|
| [campaign_worker.py](../utils/campaign_worker.py) | `_send_whatsapp()` method |

## WhatsApp Format

The worker automatically adds the `whatsapp:` prefix:
```python
whatsapp_from = f"whatsapp:{from_number}"
whatsapp_to = f"whatsapp:{to_number}"
```

## Important Notes

- WhatsApp requires a pre-approved template for initiating conversations
- After a user replies, you have a 24-hour window for free-form messages
- The current implementation sends the `messageBody` as-is
