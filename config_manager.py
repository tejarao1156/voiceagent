"""
Configuration manager for phone-specific AI settings.
Handles loading, caching, and fallback to defaults.
"""

from databases.mongodb_db import get_mongo_db, is_mongodb_available
from config import (
    VOICE_MODEL, TTS_MODEL, INFERENCE_MODEL
)
import logging
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)

# Default system prompt when no phone-specific config exists
DEFAULT_SYSTEM_PROMPT = "You are a helpful voice agent. Provide concise, natural responses in a friendly tone."


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
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"✅ Using cached config for {normalized_number}")
                return self.config_cache[normalized_number]
            else:
                # Cache expired, remove it
                logger.debug(f"⏰ Cache expired for {normalized_number}, refreshing...")
                self.config_cache.pop(normalized_number, None)
                self._cache_timestamps.pop(normalized_number, None)

        # Query MongoDB for phone config
        mongo_config = await self._get_phone_config_from_db(normalized_number)

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
        self.config_cache[normalized_number] = config
        self._cache_timestamps[normalized_number] = time.time()

        return config

    async def _get_phone_config_from_db(self, phone_number: str) -> Optional[Dict]:
        """
        Fetch configuration for a specific phone number from MongoDB.

        Args:
            phone_number: Twilio phone number (e.g., +1234567890)

        Returns:
            Configuration dict or None if not found
        """
        try:
            if not is_mongodb_available():
                logger.warning("MongoDB not available, cannot fetch config")
                return None

            db = get_mongo_db()
            if db is None:
                logger.warning("MongoDB database not available")
                return None

            # Query phone_configs collection
            config = await db.phone_configs.find_one({
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
            if not is_mongodb_available():
                logger.warning("MongoDB not available, cannot save config")
                return False

            db = get_mongo_db()
            if db is None:
                logger.warning("MongoDB database not available")
                return False

            phone_number = config.get("phone_number")
            if not phone_number:
                logger.error("phone_number is required in config")
                return False

            # Add updated_at timestamp
            from datetime import datetime
            config["updated_at"] = datetime.utcnow()

            # If creating new, add created_at
            existing = await db.phone_configs.find_one({"phone_number": phone_number})
            if not existing:
                config["created_at"] = datetime.utcnow()

            result = await db.phone_configs.update_one(
                {"phone_number": phone_number},
                {"$set": config},
                upsert=True
            )

            logger.info(f"✅ Config saved for {phone_number} (upserted: {result.upserted_id is not None})")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
            return False

    async def list_phone_configs(self, include_inactive: bool = False) -> list:
        """
        List all phone configurations.

        Args:
            include_inactive: If True, include inactive configs

        Returns:
            List of configuration dictionaries
        """
        try:
            if not is_mongodb_available():
                logger.warning("MongoDB not available, cannot list configs")
                return []

            db = get_mongo_db()
            if db is None:
                logger.warning("MongoDB database not available")
                return []

            query = {} if include_inactive else {"is_active": True}

            cursor = db.phone_configs.find(query)
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
            if not is_mongodb_available():
                logger.warning("MongoDB not available, cannot delete config")
                return False

            db = get_mongo_db()
            if db is None:
                logger.warning("MongoDB database not available")
                return False

            from datetime import datetime

            if hard_delete:
                result = await db.phone_configs.delete_one({"phone_number": phone_number})
                logger.info(f"✅ Hard deleted config for {phone_number}")
                return result.deleted_count > 0
            else:
                result = await db.phone_configs.update_one(
                    {"phone_number": phone_number},
                    {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
                )
                logger.info(f"✅ Soft deleted (deactivated) config for {phone_number}")
                return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Error deleting config: {e}")
            return False

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
