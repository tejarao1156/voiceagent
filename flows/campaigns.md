# Campaigns Flow

Full lifecycle of campaign management: creation, execution, pause/resume, and crash recovery.

## Campaign States

```mermaid
stateDiagram-v2
    [*] --> draft: Create
    draft --> scheduled: Schedule
    draft --> running: Start
    scheduled --> running: Time reached
    running --> paused: Pause
    paused --> running: Resume
    running --> completed: All items processed
    running --> failed: Error
```

## Data Flow

```mermaid
sequenceDiagram
    participant UI
    participant API as api_general.py
    participant Store as MongoDBCampaignStore
    participant Worker as CampaignWorker
    participant Twilio

    Note over UI,Twilio: Campaign Creation
    UI->>API: POST /api/campaigns
    API->>Store: create_campaign()
    Store->>Store: Insert campaign doc
    Store->>Store: Insert N campaign_items (pending)
    
    Note over UI,Twilio: Start Campaign
    UI->>API: POST /api/campaigns/{id}/start
    API->>Store: update status = running
    
    Note over Worker,Twilio: Background Processing
    loop Every 5 seconds
        Worker->>Store: Check running campaigns
        Worker->>Store: acquire_pending_items(10)
        Note over Store: Atomic lock: pending → in_progress
        Worker->>Twilio: Send batch (parallel)
        Worker->>Store: Update items → sent/failed
        Worker->>Store: Update campaign stats
    end
    
    Note over Worker: Completion
    Worker->>Store: No more pending → status = completed
```

## Crash Recovery

```mermaid
flowchart TD
    A[Worker Starts] --> B[_recover_from_crash]
    B --> C{Running campaigns?}
    C -->|Yes| D[Find in_progress items]
    D --> E[Reset to pending]
    E --> F[Continue processing]
    C -->|No| F
```

## Key Files

| File | Purpose |
|------|---------|
| [campaign_worker.py](../utils/campaign_worker.py) | Background worker |
| [mongodb_campaign_store.py](../databases/mongodb_campaign_store.py) | Campaign & items CRUD |
| [mongodb_campaign_execution_store.py](../databases/mongodb_campaign_execution_store.py) | Execution logs |

## Database Schema

### `campaigns` Collection
```json
{
  "_id": ObjectId,
  "name": "Marketing Blast",
  "type": "sms|voice|whatsapp",
  "status": "draft|scheduled|running|paused|completed|failed",
  "config": {
    "fromNumber": "+15551234567",
    "promptId": "...",
    "messageBody": "Hello!..."
  },
  "stats": {
    "total": 1000,
    "pending": 500,
    "sent": 480,
    "failed": 20
  },
  "progress_percent": 50.0
}
```

### `campaign_items` Collection
```json
{
  "_id": ObjectId,
  "campaign_id": ObjectId,
  "phone_number": "+15559876543",
  "status": "pending|in_progress|sent|failed",
  "locked_at": "2024-01-01T12:00:00Z",
  "result": "SM123..." 
}
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/campaigns` | List all campaigns |
| POST | `/api/campaigns` | Create new campaign |
| GET | `/api/campaigns/{id}` | Get campaign details |
| POST | `/api/campaigns/{id}/start` | Start campaign |
| POST | `/api/campaigns/{id}/pause` | Pause campaign |
| DELETE | `/api/campaigns/{id}` | Delete campaign |
