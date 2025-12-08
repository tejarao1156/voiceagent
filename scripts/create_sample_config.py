"""
Create a sample phone configuration for testing.

Usage:
    python scripts/create_sample_config.py
    
    # Or with a specific phone number:
    TWILIO_PHONE_NUMBER=+18668134984 python scripts/create_sample_config.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from databases.mongodb_db import initialize_mongodb
from config_manager import config_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_sample_config():
    """Create a sample phone configuration"""
    try:
        # Initialize MongoDB connection
        initialize_mongodb()

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

        logger.info(f"📞 Creating sample config for {phone_number}...")
        
        success = await config_manager.save_phone_config(sample_config)
        
        if success:
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"✅ Sample config created for {phone_number}")
            logger.info("=" * 60)
            logger.info(f"   Display Name: {sample_config['display_name']}")
            logger.info(f"   TTS Voice: {sample_config['tts_voice']}")
            logger.info(f"   LLM Model: {sample_config['inference_model']}")
            logger.info(f"   Greeting: {sample_config['greeting']}")
            logger.info("")
            logger.info("Next steps:")
            logger.info(f"  1. Make a call to {phone_number}")
            logger.info(f"  2. The AI will use this configuration")
            logger.info(f"  3. Update config via PUT /admin/phone-config/{phone_number}")
            logger.info("")

            # Invalidate cache to ensure fresh config is loaded
            config_manager.invalidate_cache(phone_number)
            return True
        else:
            logger.error("❌ Failed to create sample config")
            return False

    except Exception as e:
        logger.error(f"❌ Error creating sample config: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(create_sample_config())
    sys.exit(0 if result else 1)
