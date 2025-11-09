> **⚠️ IMPORTANT: DO NOT MODIFY THIS FILE**
> 
> This documentation file should **NOT be changed** unless explicitly requested by the user.
> Only update this file when the user specifically asks you to do so.
> 
> If you need to update the documentation, ask the user first or create a separate documentation file.

---

# Multi-Tenant Phone Number Configuration Feature - Implementation Plan

## Overview

This feature enables different Twilio phone numbers to have unique AI configurations (STT model, TTS model, inference model, voice parameters, prompts) stored in MongoDB. When a call comes in to a specific phone number, the system automatically loads and uses that number's configuration instead of global defaults.

### Architecture Flow

```
Incoming Call (Twilio Webhook)
    ↓
Extract "To" phone number from webhook data
    ↓
Query MongoDB for phone number configuration
    ↓
Load Configuration:
  - STT Model (whisper-1, etc.)
  - TTS Model (tts-1, tts-1-hd)
  - TTS Voice (alloy, echo, fable, onyx, nova, shimmer)
  - Inference Model (gpt-4o-mini, gpt-4o, etc.)
  - System Prompt (custom behavior)
  - Greeting Message
  - Temperature, Max Tokens, etc.
    ↓
Use that config for entire call lifecycle
    ↓
All STT, LLM, TTS operations use phone-specific settings
    ↓
Call ends → Config cached for future calls
```

### Key Benefits

- **Multi-Tenant Support**: Different phone numbers can have different AI personalities
- **Easy Configuration**: Change AI behavior by updating MongoDB document
- **No Code Changes**: Update config in database, no server restart needed
- **Fallback Support**: If config not found, uses sensible defaults
- **Performance**: In-memory caching for fast config lookup

---

## Phase 1: MongoDB Setup & Schema

### Step 1.1: Add MongoDB Dependencies

**File:** `requirements.txt`

Add these lines:
```
pymongo>=4.5.0
motor>=3.3.0  # Async MongoDB driver for FastAPI
```

### Step 1.2: Create MongoDB Models

**File:** `db/mongo_models.py` (NEW FILE)

```python
"""
Pydantic models for MongoDB phone number configurations.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PhoneNumberConfig(BaseModel):
    """Configuration for a specific Twilio phone number"""
    
    # Required Fields
    phone_number: str = Field(..., description="Twilio phone number (e.g., +1234567890)", example="+18668134984")
    display_name: str = Field(..., description="Human-readable name for this number", example="Customer Service Line")
    
    # Voice Processing Configuration
    stt_model: str = Field(default="whisper-1", description="Speech-to-text model ID", example="whisper-1")
    tts_model: str = Field(default="tts-1", description="Text-to-speech model (tts-1 or tts-1-hd)", example="tts-1")
    tts_voice: str = Field(default="alloy", description="TTS voice (alloy, echo, fable, onyx, nova, shimmer)", example="nova")
    
    # LLM Configuration
    inference_model: str = Field(default="gpt-4o-mini", description="OpenAI GPT model", example="gpt-4o-mini")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature (0.0-2.0)", example=0.7)
    max_tokens: int = Field(default=500, ge=1, le=4000, description="Maximum tokens for LLM response", example=500)
    
    # Behavior Configuration
    system_prompt: str = Field(..., description="Custom system prompt for AI behavior", example="You are a helpful customer support agent...")
    greeting: str = Field(..., description="Custom greeting message when call starts", example="Welcome to customer support!")
    
    # Advanced Features
    enable_interrupts: bool = Field(default=True, description="Allow user to interrupt AI responses")
    interrupt_timeout: float = Field(default=0.5, ge=0.1, le=5.0, description="Timeout for interrupt detection (seconds)")
    
    # Recording Configuration
    enable_recording: bool = Field(default=True, description="Enable call recording")
    max_call_duration: int = Field(default=3600, ge=60, description="Maximum call duration in seconds", example=3600)
    
    # Status
    is_active: bool = Field(default=True, description="Whether this configuration is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "+18668134984",
                "display_name": "Main Support Line",
                "stt_model": "whisper-1",
                "tts_model": "tts-1",
                "tts_voice": "nova",
                "inference_model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 500,
                "system_prompt": "You are a helpful customer support agent. Provide concise, friendly responses.",
                "greeting": "Welcome to customer support! How can I help you today?",
                "enable_interrupts": True,
                "interrupt_timeout": 0.5,
                "enable_recording": True,
                "max_call_duration": 3600,
                "is_active": True
            }
        }
```

---

## Phase 2: MongoDB Connection Layer

### Step 2.1: Create MongoDB Client

**File:** `db/mongodb.py` (NEW FILE)

```python
"""
MongoDB connection and operations for phone number configurations.
"""

from motor.motor_asyncio import AsyncClient, AsyncDatabase
from config import MONGODB_URL, MONGODB_DB_NAME
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class MongoDBClient:
    """Async MongoDB client for phone configuration management"""
    
    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.db: Optional[AsyncDatabase] = None
        self._connected = False
    
    async def connect(self):
        """Initialize MongoDB connection and create indexes"""
        try:
            if self._connected:
                logger.info("MongoDB already connected")
                return
            
            self.client = AsyncClient(MONGODB_URL)
            self.db = self.client[MONGODB_DB_NAME]
            
            # Create indexes for faster queries
            try:
                await self.db.phone_configs.create_index("phone_number", unique=True)
                await self.db.phone_configs.create_index("is_active")
                logger.info("✅ MongoDB indexes created")
            except Exception as e:
                logger.warning(f"Index creation warning (may already exist): {e}")
            
            # Test connection
            await self.client.admin.command('ping')
            self._connected = True
            logger.info(f"✅ MongoDB connected to {MONGODB_URL}/{MONGODB_DB_NAME}")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self._connected = False
            raise
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("✅ MongoDB disconnected")
    
    async def get_phone_config(self, phone_number: str) -> Optional[Dict]:
        """
        Fetch configuration for a specific phone number.
        
        Args:
            phone_number: Twilio phone number (e.g., +1234567890)
        
        Returns:
            Configuration dict or None if not found
        """
        try:
            if not self._connected:
                logger.warning("MongoDB not connected, cannot fetch config")
                return None
            
            config = await self.db.phone_configs.find_one({
                "phone_number": phone_number,
                "is_active": True
            })
            
            if not config:
                logger.debug(f"⚠️ No config found for {phone_number}, will use defaults")
                return None
            
            # Convert ObjectId to string for JSON serialization
            if "_id" in config:
                config["_id"] = str(config["_id"])
            
            logger.info(f"✅ Loaded config for {phone_number}: {config.get('display_name', 'Unknown')}")
            return config
        except Exception as e:
            logger.error(f"❌ Error fetching config for {phone_number}: {e}")
            return None
    
    async def save_phone_config(self, config: Dict) -> bool:
        """
        Save or update phone number configuration.
        
        Args:
            config: Configuration dictionary (must include phone_number)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._connected:
                logger.warning("MongoDB not connected, cannot save config")
                return False
            
            phone_number = config.get("phone_number")
            if not phone_number:
                logger.error("phone_number is required in config")
                return False
            
            # Add updated_at timestamp
            from datetime import datetime
            config["updated_at"] = datetime.utcnow()
            
            # If creating new, add created_at
            existing = await self.db.phone_configs.find_one({"phone_number": phone_number})
            if not existing:
                config["created_at"] = datetime.utcnow()
            
            result = await self.db.phone_configs.update_one(
                {"phone_number": phone_number},
                {"$set": config},
                upsert=True
            )
            
            logger.info(f"✅ Config saved for {phone_number} (upserted: {result.upserted_id is not None})")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
            return False
    
    async def list_phone_configs(self, include_inactive: bool = False) -> List[Dict]:
        """
        List all phone configurations.
        
        Args:
            include_inactive: If True, include inactive configs
        
        Returns:
            List of configuration dictionaries
        """
        try:
            if not self._connected:
                logger.warning("MongoDB not connected, cannot list configs")
                return []
            
            query = {} if include_inactive else {"is_active": True}
            
            cursor = self.db.phone_configs.find(query)
            configs = await cursor.to_list(None)
            
            # Convert ObjectIds to strings
            for config in configs:
                if "_id" in config:
                    config["_id"] = str(config["_id"])
            
            logger.info(f"✅ Listed {len(configs)} phone configs")
            return configs
        except Exception as e:
            logger.error(f"❌ Error listing configs: {e}")
            return []
    
    async def delete_phone_config(self, phone_number: str, hard_delete: bool = False) -> bool:
        """
        Delete or deactivate phone configuration.
        
        Args:
            phone_number: Phone number to delete
            hard_delete: If True, permanently delete. If False, soft delete (set is_active=False)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._connected:
                logger.warning("MongoDB not connected, cannot delete config")
                return False
            
            if hard_delete:
                result = await self.db.phone_configs.delete_one({"phone_number": phone_number})
                logger.info(f"✅ Hard deleted config for {phone_number}")
            else:
                result = await self.db.phone_configs.update_one(
                    {"phone_number": phone_number},
                    {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
                )
                logger.info(f"✅ Soft deleted (deactivated) config for {phone_number}")
            
            return result.modified_count > 0 or result.deleted_count > 0
        except Exception as e:
            logger.error(f"❌ Error deleting config: {e}")
            return False

# Global MongoDB client instance
mongodb = MongoDBClient()
```

---

## Phase 3: Configuration Manager

### Step 3.1: Create Configuration Manager

**File:** `config_manager.py` (NEW FILE)

```python
"""
Configuration manager for phone-specific AI settings.
Handles loading, caching, and fallback to defaults.
"""

from db.mongodb import mongodb
from config import (
    VOICE_MODEL, TTS_MODEL, INFERENCE_MODEL,
    DEFAULT_SYSTEM_PROMPT
)
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class PhoneConfigManager:
    """Manages phone-specific AI configurations with caching"""
    
    def __init__(self):
        self.config_cache: Dict[str, Dict] = {}  # In-memory cache: phone_number -> config
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        self._cache_timestamps: Dict[str, float] = {}  # Track when configs were cached
    
    async def get_config_for_call(self, to_number: str) -> Dict:
        """
        Get the configuration for an incoming call based on the 'To' phone number.
        Falls back to defaults if not found in MongoDB.
        
        Args:
            to_number: The phone number being called (from Twilio webhook "To" field)
        
        Returns:
            Configuration dictionary with all AI settings
        """
        # Normalize phone number (ensure it starts with +)
        normalized_number = self._normalize_phone_number(to_number)
        
        # Check cache first
        if normalized_number in self.config_cache:
            timestamp = self._cache_timestamps.get(normalized_number, 0)
            import time
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"✅ Using cached config for {normalized_number}")
                return self.config_cache[normalized_number]
            else:
                # Cache expired, remove it
                logger.debug(f"⏰ Cache expired for {normalized_number}, refreshing...")
                self.config_cache.pop(normalized_number, None)
                self._cache_timestamps.pop(normalized_number, None)
        
        # Query MongoDB
        mongo_config = await mongodb.get_phone_config(normalized_number)
        
        if mongo_config:
            # Build config from MongoDB document
            config = {
                "phone_number": mongo_config.get("phone_number", normalized_number),
                "display_name": mongo_config.get("display_name", "Unknown"),
                "stt_model": mongo_config.get("stt_model", VOICE_MODEL),
                "tts_model": mongo_config.get("tts_model", TTS_MODEL),
                "tts_voice": mongo_config.get("tts_voice", "alloy"),
                "inference_model": mongo_config.get("inference_model", INFERENCE_MODEL),
                "temperature": mongo_config.get("temperature", 0.7),
                "max_tokens": mongo_config.get("max_tokens", 500),
                "system_prompt": mongo_config.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
                "greeting": mongo_config.get("greeting", "Hello! How can I help you today?"),
                "enable_interrupts": mongo_config.get("enable_interrupts", True),
                "interrupt_timeout": mongo_config.get("interrupt_timeout", 0.5),
                "enable_recording": mongo_config.get("enable_recording", True),
                "max_call_duration": mongo_config.get("max_call_duration", 3600),
            }
            logger.info(f"✅ Loaded MongoDB config for {normalized_number}: {config['display_name']}")
        else:
            # Use defaults
            logger.info(f"⚠️ Using default config for {normalized_number} (no MongoDB config found)")
            config = {
                "phone_number": normalized_number,
                "display_name": "Default Configuration",
                "stt_model": VOICE_MODEL,
                "tts_model": TTS_MODEL,
                "tts_voice": "alloy",
                "inference_model": INFERENCE_MODEL,
                "temperature": 0.7,
                "max_tokens": 500,
                "system_prompt": DEFAULT_SYSTEM_PROMPT,
                "greeting": "Hello! How can I help you today?",
                "enable_interrupts": True,
                "interrupt_timeout": 0.5,
                "enable_recording": True,
                "max_call_duration": 3600,
            }
        
        # Cache it
        import time
        self.config_cache[normalized_number] = config
        self._cache_timestamps[normalized_number] = time.time()
        
        return config
    
    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number format (ensure + prefix)"""
        if not phone_number:
            return phone_number
        if not phone_number.startswith("+"):
            return f"+{phone_number}"
        return phone_number
    
    def invalidate_cache(self, phone_number: Optional[str] = None):
        """
        Clear cache for specific number or all numbers.
        
        Args:
            phone_number: If provided, clear only this number. If None, clear all.
        """
        normalized = self._normalize_phone_number(phone_number) if phone_number else None
        
        if normalized:
            self.config_cache.pop(normalized, None)
            self._cache_timestamps.pop(normalized, None)
            logger.info(f"✅ Cache invalidated for {normalized}")
        else:
            self.config_cache.clear()
            self._cache_timestamps.clear()
            logger.info("✅ Cache cleared for all numbers")
    
    def get_cached_config(self, phone_number: str) -> Optional[Dict]:
        """Get config from cache without querying MongoDB"""
        normalized = self._normalize_phone_number(phone_number)
        return self.config_cache.get(normalized)

# Global configuration manager instance
config_manager = PhoneConfigManager()
```

---

## Phase 4: Update Twilio Handler

### Step 4.1: Modify Twilio Phone Tool

**File:** `tools/phone/twilio_phone/__init__.py`

**Changes needed:**

1. **Add import at top:**
```python
from config_manager import config_manager
```

2. **Add instance variable in `__init__`:**
```python
def __init__(self, ...):
    # ... existing code ...
    self.call_configs: Dict[str, Dict] = {}  # Store config per call: call_sid -> config
```

3. **Update `handle_incoming_call` method:**
```python
async def handle_incoming_call(self, call_data: Dict[str, Any]) -> str:
    """Handle incoming Twilio phone calls."""
    call_sid = call_data.get("CallSid")
    from_number = call_data.get("From")
    to_number = call_data.get("To")  # ← ADD THIS: Extract "To" number
    
    if not call_sid:
        logger.error("No CallSid in incoming call webhook")
        return self._create_error_twiml("Invalid call data")
    
    logger.info(f"Incoming call: {call_sid} from {from_number} to {to_number}")
    
    try:
        # ← ADD THIS: Load phone-specific configuration
        phone_config = await config_manager.get_config_for_call(to_number)
        
        logger.info(f"📞 Using config for {to_number}: {phone_config['display_name']}")
        logger.info(f"   STT: {phone_config['stt_model']}, TTS: {phone_config['tts_model']} ({phone_config['tts_voice']}), LLM: {phone_config['inference_model']}")
        
        # Store config for this call
        self.call_configs[call_sid] = phone_config
        
        # Create conversation session with phone-specific prompt
        session_data = self.conversation_tool.create_session(
            customer_id=f"phone_{from_number}",
            persona=None,  # We'll use system_prompt from config instead
            prompt=phone_config.get("system_prompt")  # ← Use phone-specific prompt
        )
        
        session_id = session_data.get("session_id", call_sid)
        
        # Store call mapping and session
        self.active_calls[call_sid] = session_id
        self.session_data[session_id] = session_data
        self.audio_buffers[call_sid] = []
        
        # Use phone-specific greeting
        greeting_text = phone_config.get("greeting", "Hello! How can I help you today?")
        
        # Use simple TwiML approach
        response = VoiceResponse()
        response.say(greeting_text, voice="alice")  # ← Use phone-specific greeting
        
        # Record the caller's message
        record_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/recording?CallSid={call_sid}"
        response.record(
            action=record_url,
            method="POST",
            max_speech_time=10,
            speech_timeout="auto"
        )
        
        twiml = str(response)
        logger.info(f"✅ Call {call_sid} TwiML Response Generated")
        logger.info(f"   Greeting: {greeting_text[:50]}...")
        return twiml
        
    except Exception as e:
        logger.error(f"Error handling incoming call {call_sid}: {e}")
        return self._create_error_twiml(str(e))
```

4. **Update `_process_phone_audio` method (if using Media Streams) or recording handler:**
```python
async def _process_phone_audio(self, call_sid: str, audio_data: bytes, websocket: WebSocket):
    """Process phone audio with phone-specific configuration"""
    
    # Get phone config for this call
    phone_config = self.call_configs.get(call_sid)
    if not phone_config:
        logger.warning(f"No config found for call {call_sid}, using defaults")
        phone_config = await config_manager.get_config_for_call("+0000000000")  # Fallback
    
    logger.debug(f"Processing audio for {call_sid} with config: {phone_config['display_name']}")
    
    # Use config models for STT
    stt_result = await self.speech_tool.transcribe(
        audio_data,
        "wav",
        model=phone_config["stt_model"]  # ← Use phone-specific STT model
    )
    
    if stt_result.get("success"):
        user_text = stt_result.get("text", "").strip()
        
        if user_text:
            # Get AI response with phone-specific config
            session_id = self.active_calls.get(call_sid)
            if session_id:
                session_data = self.session_data.get(session_id, {})
                
                # Use phone-specific prompt and model
                ai_response = await self.conversation_tool.generate_response(
                    session_data,
                    user_text,
                    persona=None,
                    prompt=phone_config["system_prompt"],  # ← Use phone-specific prompt
                    model=phone_config["inference_model"],  # ← Use phone-specific model
                    temperature=phone_config["temperature"],
                    max_tokens=phone_config["max_tokens"]
                )
                
                response_text = ai_response.get("response", "I'm sorry, I didn't understand that.")
                
                # Use phone-specific TTS
                tts_result = await self.tts_tool.synthesize(
                    response_text,
                    voice=phone_config["tts_voice"],  # ← Use phone-specific voice
                    model=phone_config["tts_model"]  # ← Use phone-specific TTS model
                )
                
                # Send audio response...
```

5. **Update recording handler in `api_general.py`:**
```python
@app.post("/webhooks/twilio/recording")
async def twilio_recording_handler(request: Request):
    """Handle recorded audio from caller"""
    try:
        from twilio.twiml.voice_response import VoiceResponse
        from config_manager import config_manager
        
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        recording_url = form_data.get("RecordingUrl")
        to_number = form_data.get("To")  # ← ADD THIS
        
        logger.info(f"[RECORDING] Call {call_sid} to {to_number}")
        
        # ← ADD THIS: Load phone-specific config
        phone_config = await config_manager.get_config_for_call(to_number)
        logger.info(f"[RECORDING] Using config: {phone_config['display_name']}")
        
        # Store config for this call
        twilio_phone_tool.call_configs[call_sid] = phone_config
        
        response = VoiceResponse()
        
        if recording_url:
            # Download and process recording...
            # Use phone_config["stt_model"] for STT
            # Use phone_config["system_prompt"], phone_config["inference_model"] for LLM
            # Use phone_config["tts_voice"], phone_config["tts_model"] for TTS
            # ... rest of existing code ...
```

---

## Phase 5: Add Admin API Endpoints

### Step 5.1: Add Configuration Management Endpoints

**File:** `api_general.py`

**Add these endpoints after the existing Twilio endpoints:**

```python
# ============================================================================
# PHONE CONFIGURATION MANAGEMENT ENDPOINTS (Admin)
# ============================================================================

@app.post(
    "/admin/phone-config",
    summary="Create or Update Phone Configuration",
    description="Create or update AI configuration for a specific Twilio phone number",
    tags=["Phone Configuration"],
    response_model=Dict[str, Any]
)
async def create_phone_config(config_data: Dict[str, Any]):
    """
    Create or update configuration for a phone number.
    
    Example request body:
    ```json
    {
        "phone_number": "+18668134984",
        "display_name": "Sales Line",
        "stt_model": "whisper-1",
        "tts_model": "tts-1",
        "tts_voice": "nova",
        "inference_model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 500,
        "system_prompt": "You are a sales representative...",
        "greeting": "Welcome to our sales team!",
        "enable_interrupts": true,
        "interrupt_timeout": 0.5,
        "enable_recording": true,
        "max_call_duration": 3600,
        "is_active": true
    }
    ```
    """
    try:
        from db.mongodb import mongodb
        from config_manager import config_manager
        from db.mongo_models import PhoneNumberConfig
        
        # Validate required fields
        phone_number = config_data.get("phone_number")
        if not phone_number:
            raise HTTPException(status_code=400, detail="phone_number is required")
        
        # Validate using Pydantic model (will raise ValidationError if invalid)
        try:
            validated_config = PhoneNumberConfig(**config_data)
            config_dict = validated_config.dict(exclude_none=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
        
        # Save to MongoDB
        success = await mongodb.save_phone_config(config_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Invalidate cache for this number
        config_manager.invalidate_cache(phone_number)
        
        logger.info(f"✅ Phone config saved: {phone_number}")
        
        return {
            "success": True,
            "message": f"Configuration saved for {phone_number}",
            "config": config_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/admin/phone-config/{phone_number}",
    summary="Get Phone Configuration",
    description="Retrieve AI configuration for a specific phone number",
    tags=["Phone Configuration"],
    response_model=Dict[str, Any]
)
async def get_phone_config(phone_number: str):
    """Get configuration for a specific phone number"""
    try:
        from db.mongodb import mongodb
        
        config = await mongodb.get_phone_config(phone_number)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Configuration not found for {phone_number}. Use POST /admin/phone-config to create one."
            )
        
        return {
            "success": True,
            "config": config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/admin/phone-configs",
    summary="List All Phone Configurations",
    description="List all active phone number configurations",
    tags=["Phone Configuration"],
    response_model=Dict[str, Any]
)
async def list_phone_configs(include_inactive: bool = Query(False, description="Include inactive configs")):
    """List all phone configurations"""
    try:
        from db.mongodb import mongodb
        
        configs = await mongodb.list_phone_configs(include_inactive=include_inactive)
        
        return {
            "success": True,
            "total": len(configs),
            "configs": configs
        }
    except Exception as e:
        logger.error(f"Error listing phone configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/admin/phone-config/{phone_number}",
    summary="Update Phone Configuration",
    description="Update existing configuration for a phone number (partial update supported)",
    tags=["Phone Configuration"],
    response_model=Dict[str, Any]
)
async def update_phone_config(phone_number: str, config_updates: Dict[str, Any]):
    """Update configuration for a phone number (partial updates allowed)"""
    try:
        from db.mongodb import mongodb
        from config_manager import config_manager
        
        # Get existing config
        existing = await mongodb.get_phone_config(phone_number)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Configuration not found for {phone_number}")
        
        # Merge updates
        updated_config = {**existing, **config_updates}
        updated_config["phone_number"] = phone_number  # Ensure phone_number doesn't change
        
        # Validate
        from db.mongo_models import PhoneNumberConfig
        try:
            validated_config = PhoneNumberConfig(**updated_config)
            config_dict = validated_config.dict(exclude_none=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
        
        # Save
        success = await mongodb.save_phone_config(config_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update configuration")
        
        # Invalidate cache
        config_manager.invalidate_cache(phone_number)
        
        logger.info(f"✅ Phone config updated: {phone_number}")
        
        return {
            "success": True,
            "message": f"Configuration updated for {phone_number}",
            "config": config_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/admin/phone-config/{phone_number}",
    summary="Delete Phone Configuration",
    description="Delete (deactivate) configuration for a phone number",
    tags=["Phone Configuration"],
    response_model=Dict[str, Any]
)
async def delete_phone_config(
    phone_number: str,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete")
):
    """Delete configuration for a phone number"""
    try:
        from db.mongodb import mongodb
        from config_manager import config_manager
        
        success = await mongodb.delete_phone_config(phone_number, hard_delete=hard_delete)
        if not success:
            raise HTTPException(status_code=404, detail=f"Configuration not found for {phone_number}")
        
        # Invalidate cache
        config_manager.invalidate_cache(phone_number)
        
        logger.info(f"✅ Phone config deleted: {phone_number} (hard_delete={hard_delete})")
        
        return {
            "success": True,
            "message": f"Configuration {'permanently deleted' if hard_delete else 'deactivated'} for {phone_number}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting phone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Phase 6: Update Configuration Files

### Step 6.1: Update `config.py`

**File:** `config.py`

**Add these lines:**

```python
# ============================================================================
# MONGODB CONFIGURATION
# ============================================================================
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "voiceagent")

# ============================================================================
# DEFAULT SYSTEM PROMPT
# ============================================================================
DEFAULT_SYSTEM_PROMPT = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "You are a helpful voice agent. Provide concise, natural responses in a friendly tone."
)
```

### Step 6.2: Update `.env.example`

**File:** `.env.example`

**Add these lines:**

```bash
# ============================================================================
# MONGODB CONFIGURATION (for phone number configurations)
# ============================================================================
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=voiceagent

# Default System Prompt (used when no phone-specific config exists)
DEFAULT_SYSTEM_PROMPT=You are a helpful voice agent. Provide concise, natural responses in a friendly tone.
```

### Step 6.3: Update `main.py` Startup/Shutdown

**File:** `main.py`

**Add MongoDB connection management:**

```python
from db.mongodb import mongodb

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize MongoDB connection
        await mongodb.connect()
        logger.info("✅ Voice Agent started with multi-tenant phone config support")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e}. Phone configs will use defaults.")
        # Continue startup even if MongoDB fails (graceful degradation)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        await mongodb.disconnect()
        logger.info("✅ MongoDB disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting MongoDB: {e}")
```

---

## Phase 7: Database Setup Scripts

### Step 7.1: Create MongoDB Setup Script

**File:** `scripts/setup_mongodb.py` (NEW FILE)

```python
"""
Setup script for MongoDB phone configuration collections.
Run this once to initialize the database schema.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.mongodb import mongodb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_mongodb():
    """Initialize MongoDB collections and indexes"""
    try:
        logger.info("🔧 Setting up MongoDB for phone configurations...")
        
        # Connect to MongoDB
        await mongodb.connect()
        
        # Create phone_configs collection (if it doesn't exist)
        # MongoDB creates collections automatically on first insert, but we can create it explicitly
        try:
            # Check if collection exists
            collections = await mongodb.db.list_collection_names()
            if "phone_configs" not in collections:
                logger.info("Creating phone_configs collection...")
                await mongodb.db.create_collection("phone_configs")
                logger.info("✅ Collection created")
            else:
                logger.info("✅ Collection already exists")
        except Exception as e:
            logger.warning(f"Collection creation note: {e}")
        
        # Ensure indexes exist
        try:
            await mongodb.db.phone_configs.create_index("phone_number", unique=True)
            logger.info("✅ Unique index on phone_number created")
        except Exception as e:
            logger.warning(f"Index creation (may already exist): {e}")
        
        try:
            await mongodb.db.phone_configs.create_index("is_active")
            logger.info("✅ Index on is_active created")
        except Exception as e:
            logger.warning(f"Index creation (may already exist): {e}")
        
        logger.info("✅ MongoDB setup complete!")
        logger.info("")
        logger.info("You can now:")
        logger.info("  1. Create phone configs via POST /admin/phone-config")
        logger.info("  2. List configs via GET /admin/phone-configs")
        logger.info("  3. Calls to configured numbers will use their specific settings")
        
    except Exception as e:
        logger.error(f"❌ MongoDB setup failed: {e}")
        raise
    finally:
        await mongodb.disconnect()

if __name__ == "__main__":
    asyncio.run(setup_mongodb())
```

### Step 7.2: Create Sample Config Script

**File:** `scripts/create_sample_config.py` (NEW FILE)

```python
"""
Create a sample phone configuration for testing.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.mongodb import mongodb
from config_manager import config_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_sample_config():
    """Create a sample phone configuration"""
    try:
        await mongodb.connect()
        
        # Get phone number from environment or use default
        phone_number = os.getenv("TWILIO_PHONE_NUMBER", "+18668134984")
        
        sample_config = {
            "phone_number": phone_number,
            "display_name": "Sample Support Line",
            "stt_model": "whisper-1",
            "tts_model": "tts-1",
            "tts_voice": "nova",
            "inference_model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 500,
            "system_prompt": "You are a helpful customer support agent. Provide concise, friendly responses. Keep answers under 2 sentences when possible.",
            "greeting": "Welcome to customer support! How can I help you today?",
            "enable_interrupts": True,
            "interrupt_timeout": 0.5,
            "enable_recording": True,
            "max_call_duration": 3600,
            "is_active": True
        }
        
        success = await mongodb.save_phone_config(sample_config)
        if success:
            logger.info(f"✅ Sample config created for {phone_number}")
            logger.info(f"   Display Name: {sample_config['display_name']}")
            logger.info(f"   TTS Voice: {sample_config['tts_voice']}")
            logger.info(f"   LLM Model: {sample_config['inference_model']}")
            
            # Invalidate cache
            config_manager.invalidate_cache(phone_number)
        else:
            logger.error("❌ Failed to create sample config")
            
    except Exception as e:
        logger.error(f"❌ Error creating sample config: {e}")
        raise
    finally:
        await mongodb.disconnect()

if __name__ == "__main__":
    asyncio.run(create_sample_config())
```

---

## Implementation Checklist

### Phase 1: MongoDB Setup & Schema
- [ ] Add `pymongo>=4.5.0` and `motor>=3.3.0` to `requirements.txt`
- [ ] Create `db/` directory if it doesn't exist
- [ ] Create `db/mongo_models.py` with `PhoneNumberConfig` Pydantic model
- [ ] Test model validation with sample data

### Phase 2: MongoDB Connection Layer
- [ ] Create `db/mongodb.py` with `MongoDBClient` class
- [ ] Implement `connect()`, `disconnect()`, `get_phone_config()`, `save_phone_config()`, `list_phone_configs()`, `delete_phone_config()`
- [ ] Add proper error handling and logging
- [ ] Test MongoDB connection locally

### Phase 3: Configuration Manager
- [ ] Create `config_manager.py` with `PhoneConfigManager` class
- [ ] Implement `get_config_for_call()` with caching and fallback logic
- [ ] Add `invalidate_cache()` method
- [ ] Test config loading with and without MongoDB configs

### Phase 4: Update Twilio Handler
- [ ] Add `from config_manager import config_manager` to `tools/phone/twilio_phone/__init__.py`
- [ ] Add `self.call_configs: Dict[str, Dict] = {}` to `__init__`
- [ ] Update `handle_incoming_call()` to extract `to_number` and load config
- [ ] Update recording handler in `api_general.py` to use phone config
- [ ] Update all STT, LLM, TTS calls to use config values
- [ ] Test with a call to verify config is loaded correctly

### Phase 5: Admin API Endpoints
- [ ] Add `POST /admin/phone-config` endpoint (create/update)
- [ ] Add `GET /admin/phone-config/{phone_number}` endpoint (get)
- [ ] Add `GET /admin/phone-configs` endpoint (list all)
- [ ] Add `PUT /admin/phone-config/{phone_number}` endpoint (update)
- [ ] Add `DELETE /admin/phone-config/{phone_number}` endpoint (delete)
- [ ] Test all endpoints via Swagger UI or curl

### Phase 6: Configuration Files
- [ ] Update `config.py` with `MONGODB_URL`, `MONGODB_DB_NAME`, `DEFAULT_SYSTEM_PROMPT`
- [ ] Update `.env.example` with MongoDB configuration
- [ ] Update `main.py` with MongoDB startup/shutdown events
- [ ] Test server startup with MongoDB connected and disconnected

### Phase 7: Database Setup Scripts
- [ ] Create `scripts/` directory if it doesn't exist
- [ ] Create `scripts/setup_mongodb.py` for database initialization
- [ ] Create `scripts/create_sample_config.py` for testing
- [ ] Run setup script to initialize MongoDB
- [ ] Create a sample config and verify it works

### Phase 8: Testing & Validation
- [ ] Test with MongoDB connected: Create config, make call, verify phone-specific settings used
- [ ] Test with MongoDB disconnected: Verify graceful fallback to defaults
- [ ] Test cache invalidation: Update config, verify new config is used
- [ ] Test multiple phone numbers: Create different configs, verify each uses correct settings
- [ ] Test admin endpoints: CRUD operations work correctly
- [ ] Test edge cases: Invalid phone numbers, missing fields, etc.

---

## Usage Examples

### Example 1: Create Phone Configuration via API

```bash
curl -X POST http://localhost:4002/admin/phone-config \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+18668134984",
    "display_name": "Sales Line",
    "stt_model": "whisper-1",
    "tts_model": "tts-1",
    "tts_voice": "nova",
    "inference_model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 500,
    "system_prompt": "You are a sales representative. Be enthusiastic and helpful. Focus on understanding customer needs.",
    "greeting": "Welcome to our sales team! How can I help you find the perfect solution today?",
    "enable_interrupts": true,
    "interrupt_timeout": 0.5,
    "enable_recording": true,
    "max_call_duration": 3600,
    "is_active": true
  }'
```

### Example 2: Get Phone Configuration

```bash
curl http://localhost:4002/admin/phone-config/+18668134984
```

### Example 3: List All Configurations

```bash
curl http://localhost:4002/admin/phone-configs
```

### Example 4: Update Configuration

```bash
curl -X PUT http://localhost:4002/admin/phone-config/+18668134984 \
  -H "Content-Type: application/json" \
  -d '{
    "tts_voice": "shimmer",
    "greeting": "Hello! Thanks for calling. How can I assist you?"
  }'
```

### Example 5: Deactivate Configuration

```bash
curl -X DELETE http://localhost:4002/admin/phone-config/+18668134984
```

### Example 6: Setup MongoDB and Create Sample Config

```bash
# 1. Start MongoDB (if using Docker)
docker run -d -p 27017:27017 --name mongodb mongo

# 2. Setup MongoDB collections
python scripts/setup_mongodb.py

# 3. Create sample configuration
python scripts/create_sample_config.py

# 4. Verify configuration
curl http://localhost:4002/admin/phone-configs
```

---

## Testing Guide

### Test Scenario 1: Basic Configuration Loading

1. **Setup:**
   ```bash
   # Start MongoDB
   docker run -d -p 27017:27017 mongo
   
   # Setup database
   python scripts/setup_mongodb.py
   
   # Create config
   python scripts/create_sample_config.py
   ```

2. **Test:**
   - Make a call to the configured phone number
   - Check logs for: `"Using config for +18668134984: Sample Support Line"`
   - Verify greeting matches config
   - Verify TTS voice matches config (listen to response)

### Test Scenario 2: Fallback to Defaults

1. **Setup:**
   - Stop MongoDB or use unconfigured phone number

2. **Test:**
   - Make a call to an unconfigured number
   - Check logs for: `"Using default config for +1234567890 (no MongoDB config found)"`
   - Verify system uses default values from `config.py`

### Test Scenario 3: Multiple Phone Numbers

1. **Setup:**
   - Create config for `+18668134984` with voice "nova" and greeting "Sales line"
   - Create config for `+18668134985` with voice "shimmer" and greeting "Support line"

2. **Test:**
   - Call first number → Should hear "Sales line" with "nova" voice
   - Call second number → Should hear "Support line" with "shimmer" voice

### Test Scenario 4: Configuration Update

1. **Setup:**
   - Create config with greeting "Hello"

2. **Test:**
   - Update config via API to greeting "Hi there"
   - Make call → Should hear "Hi there" (new greeting)
   - Verify cache invalidation worked

---

## Troubleshooting

### Issue: MongoDB Connection Failed

**Symptoms:** Logs show `"MongoDB connection failed"` or `"MongoDB not connected"`

**Solutions:**
1. Verify MongoDB is running: `docker ps` or `mongosh --eval "db.adminCommand('ping')"`
2. Check `MONGODB_URL` in `.env`: Should be `mongodb://localhost:27017`
3. Check MongoDB logs for errors
4. System will fallback to defaults if MongoDB unavailable (graceful degradation)

### Issue: Config Not Loading

**Symptoms:** Calls use default config even though MongoDB has config

**Solutions:**
1. Check phone number format: Must match exactly (e.g., `+18668134984`)
2. Verify config is active: `is_active: true`
3. Check MongoDB query: `mongosh voiceagent --eval "db.phone_configs.find({phone_number: '+18668134984'})"`
4. Clear cache: Restart server or call `config_manager.invalidate_cache()`

### Issue: Config Changes Not Applied

**Symptoms:** Updated config but calls still use old settings

**Solutions:**
1. Cache invalidation: Configs are cached for 5 minutes. Restart server or wait.
2. Verify update succeeded: `GET /admin/phone-config/{number}` to check MongoDB
3. Check logs for cache invalidation message

### Issue: Admin Endpoints Return 404

**Symptoms:** `POST /admin/phone-config` returns 404

**Solutions:**
1. Verify endpoints are added to `api_general.py`
2. Check server logs for import errors
3. Restart server after adding endpoints
4. Verify endpoint path: Should be `/admin/phone-config` (not `/admin/phone-configs`)

---

## Performance Considerations

### Caching Strategy

- **In-Memory Cache:** Configs are cached for 5 minutes (300 seconds)
- **Cache Invalidation:** Automatically invalidated on config updates
- **Cache Size:** Minimal memory footprint (one dict per phone number)

### MongoDB Queries

- **Indexes:** `phone_number` (unique) and `is_active` are indexed for fast lookups
- **Query Pattern:** Single document lookup per call (O(1) with index)
- **Connection Pooling:** Motor (async driver) handles connection pooling automatically

### Latency Impact

- **First Call:** ~10-50ms for MongoDB query (if not cached)
- **Subsequent Calls:** ~0ms (served from cache)
- **Config Update:** Immediate (cache invalidated on save)

---

## Security Considerations

### Admin Endpoints

- **No Authentication:** Admin endpoints are currently unauthenticated
- **Recommendation:** Add API key authentication or JWT tokens for production
- **Example:** Add `X-API-Key` header validation

### MongoDB Security

- **Connection String:** Store `MONGODB_URL` in `.env` (not committed)
- **Network:** Use MongoDB Atlas or restrict network access in production
- **Authentication:** Add MongoDB username/password for production

### Phone Number Validation

- **Format:** Phone numbers are normalized (ensure `+` prefix)
- **Validation:** Pydantic models validate all fields before saving

---

## Future Enhancements

1. **Authentication:** Add API key or JWT authentication for admin endpoints
2. **Web UI:** Create admin dashboard for managing phone configs
3. **Config Templates:** Pre-defined templates for common use cases
4. **Analytics:** Track which configs are used most frequently
5. **A/B Testing:** Support multiple configs per number with traffic splitting
6. **Dynamic Updates:** WebSocket or webhook for real-time config updates
7. **Config Versioning:** Track config history and rollback capability
8. **Multi-Region:** Support different configs based on caller's location

---

## Summary

This implementation plan provides a complete multi-tenant phone configuration system where:

- **Each phone number** can have unique AI settings (STT, TTS, LLM, prompts)
- **Configuration is stored** in MongoDB for easy updates without code changes
- **System gracefully falls back** to defaults if MongoDB unavailable
- **Admin API endpoints** allow full CRUD operations on configurations
- **In-memory caching** ensures fast config lookup during calls
- **Zero downtime updates** - change config in database, next call uses new settings

The system is designed to be:
- **Reliable:** Graceful degradation if MongoDB fails
- **Performant:** Caching minimizes database queries
- **Flexible:** Easy to add new configuration fields
- **Maintainable:** Clear separation of concerns (models, DB, manager, handlers)

