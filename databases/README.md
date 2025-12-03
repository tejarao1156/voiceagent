# Databases Module

This module contains database implementations for storing conversations and analytics.

## MongoDB Setup

### Configuration

MongoDB connection is configured in `config.py`:
- `MONGODB_URL`: MongoDB connection string
- `MONGODB_DATABASE`: Database name (default: "voiceagent")
- `MONGODB_CONVERSATIONS_COLLECTION`: Collection name (default: "conversations")

### Files

1. **mongodb_db.py** - MongoDB connection management
   - `initialize_mongodb()` - Initialize connection
   - `get_mongo_db()` - Get database instance
   - `is_mongodb_available()` - Check availability

2. **mongodb_models.py** - Data models
   - `ConversationMessage` - Individual message model
   - `ConversationSession` - Session model with metadata

3. **mongodb_conversation_store.py** - CRUD operations
   - `save_session()` - Save/update conversation
   - `load_session()` - Load conversation by ID
   - `add_message()` - Add message to conversation
   - `list_sessions()` - List conversations

4. **mongodb_analytics.py** - Analytics queries
   - `get_call_statistics()` - Overall statistics
   - `get_calls_by_date()` - Calls grouped by date
   - `get_calls_by_agent()` - Calls grouped by agent
   - `get_recent_calls()` - Recent calls list

## Usage

### Saving a Conversation

```python
from databases.mongodb_conversation_store import MongoDBConversationStore

store = MongoDBConversationStore()
await store.save_session(session_id, session_data, agent_id="phone_number")
```

### Loading a Conversation

```python
session_data = await store.load_session(session_id)
```

### Getting Analytics

```python
from databases.mongodb_analytics import MongoDBAnalytics

analytics = MongoDBAnalytics()
stats = await analytics.get_call_statistics()
```

## API Endpoints

- `GET /analytics/call-statistics` - Get overall call statistics
- `GET /analytics/calls-by-date?days=7` - Get calls grouped by date
- `GET /analytics/calls-by-agent` - Get calls grouped by agent
- `GET /analytics/recent-calls?limit=10` - Get recent calls

