# MongoDB Schema Update - Messages Collection

## Date: 2025-11-25

## Overview
Restructured the MongoDB `messages` collection to store `user_number` at the document level (same level as `agent_id`), creating one document per unique `agent_id` + `user_number` combination.

---

## Schema Change

### ❌ Old Structure:
```json
{
  "_id": ObjectId("..."),
  "agent_id": "+12242423142",
  "created_at": "2025-11-24T22:04:53.853605",
  "updated_at": "2025-11-24T22:34:46.711674",
  "messages": [
    {
      "message_sid": "SM...",
      "user_number": "+19379935869",  // Inside message object
      "agent_number": "+12242423142",
      "body": "Hello",
      "conversation_id": "uuid",
      "direction": "inbound",
      "role": "user",
      "timestamp": "..."
    },
    // ... more messages from different users
  ]
}
```

**Problem**: One document per agent_id, all users' messages mixed together.

---

### ✅ New Structure:
```json
{
  "_id": ObjectId("..."),
  "agent_id": "+12242423142",        // Document level
  "user_number": "+19379935869",     // Document level (NEW!)
  "created_at": "2025-11-24T22:04:53.853605",
  "updated_at": "2025-11-24T22:34:46.711674",
  "messages": [
    {
      "message_sid": "SM...",
      "agent_number": "+12242423142",
      "body": "Hello",
      "conversation_id": "uuid",
      "direction": "inbound",
      "role": "user",
      "timestamp": "..."
    },
    // ... more messages from THIS user only
  ]
}
```

**Benefit**: One document per `agent_id` + `user_number` combination. Clean separation, efficient queries.

---

## Key Changes

### 1. Document Key Structure
- **Old**: `{ agent_id: "+12242423142" }` (one document per agent)
- **New**: `{ agent_id: "+12242423142", user_number: "+19379935869" }` (one document per conversation)

### 2. Query Efficiency
- **Old**: Find document by agent_id, then filter messages by user_number
- **New**: Find document directly by agent_id + user_number (compound key)

### 3. Message Storage
- **Old**: `user_number` stored inside each message object
- **New**: `user_number` stored at document level (removed from message objects)

---

## Updated Methods

### ✅ `create_message()`
- Uses compound key: `{ agent_id, user_number }`
- Normalizes phone numbers
- Creates new document if combination doesn't exist
- Logs new vs existing conversation

### ✅ `create_outbound_message()`
- Uses compound key: `{ agent_id, user_number }`
- Normalizes phone numbers
- Stores outbound messages in same document

### ✅ `check_conversation_exists()`
- Simple `find_one()` with compound key
- No need to iterate through messages
- Much faster query

### ✅ `get_last_24h_messages()`
- Finds document by compound key
- Filters messages by timestamp (last 24 hours)
- Returns sorted messages

### ✅ `get_conversation_id()`
- Finds document by compound key
- Gets conversation_id from most recent message
- No need to search through all messages

### ✅ `get_all_messages_by_agent_id()`
- Finds all documents for agent_id
- Combines messages from all user conversations
- Adds user_number from document level to each message

### ✅ `get_all_messages()`
- Works with new structure
- Gets user_number from document level
- Supports filtering by conversation_id

### ✅ `get_conversations()`
- Uses user_number from document level
- Groups by agent_id + user_number
- Returns all conversations for UI

---

## Flow with New Structure

### Incoming Message Flow:
```
1. User sends message (from_number, to_number)
   ↓
2. Normalize: agent_id = normalize(to_number), user_number = normalize(from_number)
   ↓
3. Check if document exists: { agent_id, user_number }
   ↓
4a. If EXISTS:
    - Get document
    - Get last 24 hours of messages
    - Send to LLM
    - Add new message to messages array
   ↓
4b. If NOT EXISTS:
    - Create new document with { agent_id, user_number }
    - Add message to messages array
    - Send to LLM (empty history)
   ↓
5. Store AI response in same document
```

### Benefits:
- ✅ Faster queries (direct document lookup)
- ✅ Cleaner data structure
- ✅ Easier to manage conversations
- ✅ Better scalability
- ✅ Supports all requirements (24h filtering, etc.)

---

## Migration Notes

### For Existing Data:
- Old documents (with agent_id only) will still work
- New messages will create documents with new structure
- `get_conversations()` handles both old and new structures
- Backward compatibility maintained

### Recommended Migration:
If you have existing data, you may want to:
1. Read old documents (agent_id only)
2. Group messages by user_number
3. Create new documents (agent_id + user_number)
4. Delete old documents

**Note**: This is optional - the code handles both structures.

---

## Code Changes Summary

### Files Modified:
1. **`databases/mongodb_message_store.py`**
   - All methods updated to use compound key
   - Added `normalize_phone_number` import
   - Updated document structure throughout

### Key Updates:
- ✅ Document query: `{ agent_id, user_number }` instead of `{ agent_id }`
- ✅ Phone number normalization in all methods
- ✅ user_number removed from message objects (now at document level)
- ✅ All methods work with new structure

---

## Testing Checklist

### ✅ Code Verification:
- [x] All methods compile without errors
- [x] No linting errors
- [x] Imports are correct
- [x] Phone number normalization works

### 🔄 Integration Testing Needed:
- [ ] Test with real MongoDB
- [ ] Test message creation (new conversation)
- [ ] Test message creation (existing conversation)
- [ ] Test 24-hour message filtering
- [ ] Test conversation retrieval
- [ ] Test UI display

---

## Status: ✅ **IMPLEMENTATION COMPLETE**

All code has been updated to support the new MongoDB schema structure with `user_number` at the document level.

**Ready for testing with real MongoDB data.**

