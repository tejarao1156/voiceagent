# Authentication Implementation - Quick Reference Guide

## ✅ COMPLETED

### 1. Core Authentication
- `get_current_active_user()` dependency function ✅
- Phone store with user_id filtering ✅  
- Agent store with user_id filtering ✅
- Phone endpoints protected ✅

### 2. Protected Endpoints (PARTIAL)
- `POST /api/phones` - ✅ Protected
- `GET /api/phones` - ✅ Protected
- `DELETE /api/phones/{phone_id}` - ✅ Protected

## ⏳ REMAINING WORK

### Quick Protection Pattern

**For any endpoint, add:**
```python
async def endpoint_name(
    # existing params,
    user: Dict[str, Any] = Depends(get_current_active_user)  # ADD THIS
):
```

**Then pass user_id to store methods:**
```python
# Before:
agent_id = await agent_store.create_agent(agent_data)

# After:
agent_id = await agent_store.create_agent(agent_data, user["user_id"])
```

### Endpoints to Protect

#### Agents (api_general.py ~line 3100-4100)
- `POST /agents` create_agent - Line ~3126
- `GET /agents` list_agents - Line ~3289
- `GET /agents/{agent_id}` get_agent - Line ~3900
- `PUT /agents/{agent_id}` update_agent - Line ~3990
- `DELETE /agents/{agent_id}` delete_agent - Line ~4083

#### Message Agents (search for "/api/message-agents")
- `POST /api/message-agents` create_message_agent
- `GET /api/message-agents` list_message_agents  
- `DELETE /api/message-agents/{agent_id}` delete_message_agent

#### Calls (search for "/api/calls")
- `GET /api/calls` get_all_calls
- `GET /api/calls/active` get_active_calls

#### Messages (search for "/api/messages")
- `GET /api/messages` get_messages
- `GET /api/messages/conversations` get_conversations

#### Prompts (search for "/api/prompts")
- `POST /api/prompts` create_prompt
- `GET /api/prompts` list_prompts
- `DELETE /api/prompts/{prompt_id}` delete_prompt

#### Scheduled Calls (search for "/api/scheduled-calls")
- `POST /api/scheduled-calls` create_scheduled_call
- `GET /api/scheduled-calls` list_scheduled_calls

#### Analytics (search for "/analytics")
- `GET /analytics/calls-by-date`
- `GET /analytics/calls-by-hour`

### Database Stores to Update

#### mongodb_message_agent_store.py
```python
async def create_agent(self, agent_data: Dict, user_id: str) -> Optional[str]:
    agent_data["userId"] = user_id
    # ... insert logic

async def list_agents(self, ..., user_id: Optional[str] = None) -> List[Dict]:
    query = {"isDeleted": {"$ne": True}}
    if user_id:
        query["userId"] = user_id
    # ... find logic
```

#### mongodb_call_store.py
```python
# Calls get user_id from phone number owner
async def create_call(self, call_data: Dict) -> Optional[str]:
    # Get phone's user_id
    phone = await phone_store.get_phone_by_number(call_data["to"])
    if phone:
        call_data["userId"] = phone.get("userId")
    # ... insert

async def get_all_calls(self, ..., user_id: Optional[str] = None) -> List:
    query = {}
    if user_id:
        query["userId"] = user_id
```

#### mongodb_message_store.py
```python
async def store_message(self, ..., user_id: Optional[str] = None):
    message_data["userId"] = user_id
    
async def get_messages(self, ..., user_id: Optional[str] = None):
    query = {}
    if user_id:
        query["userId"] = user_id
```

#### mongodb_scheduled_call_store.py  
```python
async def create_scheduled_call(self, call_data: Dict, user_id: str):
    call_data["userId"] = user_id
    
async def list_scheduled_calls(self, ..., user_id: Optional[str] = None):
    query = {"isDeleted": {"$ne": True}}
    if user_id:
        query["userId"] = user_id
```

#### mongodb_prompt_store.py
```python
async def create_prompt(self, prompt_data: Dict, user_id: str):
    prompt_data["userId"] = user_id
    
async def list_prompts(self, ..., user_id: Optional[str] = None):
    query = {"isDeleted": {"$ne": True}}
    if user_id:
        query["userId"] = user_id
```

## 🔍 Search Commands to Find Endpoints

```bash
# Find all agent endpoints
grep -n "async def.*agent" api_general.py

# Find all protected endpoints needing auth
grep -n "@app.post\\|@app.get\\|@app.put\\|@app.delete" api_general.py | grep -v "webhooks\\|auth"

# Find database store methods
grep -n "async def" databases/*.py
```

## ⚠️ Exceptions (DO NOT PROTECT)

- `/auth/*` - Authentication endpoints (already public)
- `/webhooks/twilio/*` - Twilio webhooks (called by external service)
- `/health` - Health checks
- `/` - Root/UI proxy
- `/_next/*` - Next.js assets

## 📊 Progress Tracking

- Database Stores: 2/7 (29%)
- API Endpoints: 3/30+ (10%)
- Overall: ~15% Complete

**Estimated Time:** 4-6 hours remaining
