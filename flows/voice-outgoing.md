# Voice Outgoing Flow

Handles outbound voice calls initiated through campaigns, including automated dialing and AI conversation.

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

    User->>UI: Create Campaign (voice)
    UI->>API: POST /api/campaigns
    API->>Store: Create campaign + items
    Store->>Store: Insert campaign_items (pending)
    
    User->>UI: Click "Start"
    UI->>API: POST /api/campaigns/{id}/start
    API->>Store: Update status = running
    
    loop Every 5 seconds
        Worker->>Store: acquire_pending_items(10)
        Store->>Store: pending → in_progress (atomic)
        Store-->>Worker: 10 locked items
        
        par Parallel Processing
            Worker->>Twilio: Create call #1
            Worker->>Twilio: Create call #2
            Worker->>Twilio: ... calls #3-10
        end
        
        Twilio->>Recipient: Calls phone
        Recipient->>Twilio: Answers
        Note over Twilio,Recipient: Same flow as voice-incoming
        
        Worker->>Store: Update items → sent/failed
        Worker->>Store: Log to campaign_executions
    end
```

## Key Files

| File | Purpose |
|------|---------|
| [campaign_worker.py](../utils/campaign_worker.py) | Background worker for processing |
| [mongodb_campaign_store.py](../databases/mongodb_campaign_store.py) | Campaign & items storage |
| [mongodb_campaign_execution_store.py](../databases/mongodb_campaign_execution_store.py) | Execution logging |

## Database Collections

| Collection | Data Stored |
|------------|-------------|
| `campaigns` | name, type, config, status, stats, progress_percent |
| `campaign_items` | phone_number, status (pending/in_progress/sent/failed) |
| `campaign_executions` | Detailed logs for each call attempt |

## Crash Recovery

On worker startup:
1. Find all campaigns with status `running`
2. Reset any items stuck in `in_progress` → `pending`
3. Resume processing from where it left off

## Configuration

| Env Variable | Default | Description |
|--------------|---------|-------------|
| `CAMPAIGN_BATCH_SIZE` | 10 | Items processed in parallel |
| `CAMPAIGN_ITEM_DELAY_SECONDS` | 1 | Delay between batches |
