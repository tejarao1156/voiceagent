# Message Storage and Conversation Flow Explanation

## How From/To Numbers Are Stored and Mapped

### Number Terminology
- **`from_number`** = User's phone number (the person texting)
- **`to_number`** = Registered agent phone number (your Twilio number)

### MongoDB Storage Structure

The system uses **one document per agent phone number** in the `messages` collection:

```javascript
{
  "agent_id": "+18668134984",  // The registered phone number (to_number)
  "created_at": "2025-11-17T00:43:34.184030",
  "updated_at": "2025-11-24T01:32:16.022833",
  "messages": [
    {
      "message_sid": "SM123456...",
      "user_number": "+19379935869",      // from_number (user)
      "agent_number": "+18668134984",     // to_number (agent)
      "body": "Hello, can you help me?",
      "conversation_id": "2e56c840-f802-493f-8857-e2c571e0a91c",
      "direction": "inbound",
      "role": "user",
      "status": "received",
      "timestamp": "2025-11-24T01:32:13.422847"
    },
    {
      "message_sid": "SM789012...",
      "agent_number": "+18668134984",     // from_number (agent sending)
      "user_number": "+19379935869",      // to_number (user receiving)
      "body": "Of course! I'm here to help...",
      "conversation_id": "2e56c840-f802-493f-8857-e2c571e0a91c",
      "direction": "outbound",
      "role": "assistant",
      "status": "sent",
      "timestamp": "2025-11-24T01:32:16.022833"
    }
  ]
}
```

### Key Fields:
- **`agent_id`**: The registered phone number (groups all messages for this agent)
- **`user_number`**: The user's phone number
- **`agent_number`**: The agent's phone number
- **`conversation_id`**: UUID that groups messages between specific user ↔ agent pair
- **`role`**: "user" or "assistant" (for LLM context)
- **`direction`**: "inbound" or "outbound"

---

## Conversation Flow

### When a Message Arrives

**Step 1: Check for Existing Conversation**

The system calls `get_conversation_id(from_number, to_number, agent_id)`:

```python
# Searches the messages array for existing conversation between these two numbers
# Returns conversation_id if found, None if not found
```

**Step 2A: Existing Conversation Found** ✅

If `conversation_id` exists:
- **Uses the SAME conversation_id**
- **Adds new message to messages array**
- **Retrieves all previous messages** with that conversation_id
- **Passes conversation history to LLM** for context

Example:
```
User +19379935869 → Agent +18668134984
  Message 1: "Test3" (conversation_id: 2e56c840...)
  Message 2: "Hello, can you help me?" (SAME conversation_id: 2e56c840...)
```

**Step 2B: New Conversation** 🆕

If no `conversation_id` found:
- **Creates NEW UUID** as conversation_id
- **Stores message with new conversation_id**
- **Sends greeting** (first message in conversation)
- **No previous history passed to LLM**

---

## How Conversation History is Passed to LLM

### Current Implementation ✅ (Already Working!)

When a message arrives from **existing conversation**:

1. **Retrieve Conversation History** (from `get_conversation_history`):
   ```python
   # Returns all messages with same conversation_id
   [
     {"role": "user", "body": "Test3", "timestamp": "..."},
     {"role": "assistant", "body": "hi", "timestamp": "..."},
     {"role": "user", "body": "Hello, can you help me?", "timestamp": "..."}
   ]
   ```

2. **Build LLM Context** (in `twilio_sms_handler.py`):
   ```python
   # Loops through conversation_history
   # Adds each user/assistant pair to session_data
   for msg in conversation_history:
       if role == "user":
           user_message = text
       elif role == "assistant":
           add_to_conversation_history(user_message, assistant_response)
   ```

3. **LLM Sees Full Context**:
   ```
   System: [Agent's system prompt]
   
   User: Test3
   Assistant: hi
   
   User: Hello, can you help me?
   Assistant: [Generates response based on full history]
   ```

4. **Response Uses Context**:
   - LLM can reference previous messages
   - Can answer questions about past conversation
   - Maintains context across the entire thread

---

## Example Scenario

### Scenario: User Asks About Previous Conversation

**Conversation History in MongoDB:**
```javascript
{
  "conversation_id": "abc-123",
  "messages": [
    {"role": "user", "body": "I need help with my order #5678"},
    {"role": "assistant", "body": "I can help! Order #5678 is being processed."},
    {"role": "user", "body": "What was my order number again?"}  // NEW MESSAGE
  ]
}
```

**What Happens:**

1. **System retrieves** all 3 messages (conversation_id = "abc-123")

2. **LLM receives context:**
   ```
   User: I need help with my order #5678
   Assistant: I can help! Order #5678 is being processed.
   User: What was my order number again?
   ```

3. **LLM responds** with context:
   ```
   "Your order number is #5678, which we discussed earlier. It's currently being processed."
   ```

4. **New response stored** in same conversation (conversation_id = "abc-123")

---

## Key Decision Points

### How System Decides Conversation Grouping:

1. **Same User + Same Agent + Existing conversation_id** → Add to existing conversation ✅
2. **Same User + Same Agent + No conversation_id** → Create new conversation 🆕
3. **Different User + Same Agent** → Separate conversation (different conversation_id)

### When Conversation History is Passed to LLM:

✅ **ALWAYS** - The system **always retrieves and passes** conversation history for existing conversations

The LLM receives:
- Full conversation history from MongoDB
- Agent's system prompt
- New user message

This allows the agent to:
- Reference previous messages
- Answer questions about past conversation
- Maintain context throughout the thread
- Provide personalized responses

---

## Summary

✅ **From/To Number Mapping:**
- `from_number` = user's phone
- `to_number` = registered agent phone
- Stored as `user_number` and `agent_number` in MongoDB

✅ **Conversation Management:**
- Each conversation has unique `conversation_id` (UUID)
- Same user + same agent = same conversation
- Messages added to array in agent's document

✅ **History Passed to LLM:**
- System retrieves all messages with same `conversation_id`
- Full conversation history sent to LLM for context
- Agent can reference and respond about previous messages

✅ **Already Implemented:**
- Everything you described is **already working**
- The system maintains conversation context
- LLM can answer questions about previous conversation
- No changes needed!
