"""
Setup script for MongoDB phone configuration collections.
Run this once to initialize the database schema.

Usage:
    python scripts/setup_mongodb.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from databases.mongodb_db import get_mongo_db, is_mongodb_available, initialize_mongodb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_mongodb():
    """Initialize MongoDB collections and indexes for phone configurations"""
    try:
        logger.info("🔧 Setting up MongoDB for phone configurations...")

        # Initialize MongoDB connection
        initialize_mongodb()

        if not is_mongodb_available():
            logger.error("❌ MongoDB is not available. Please ensure MongoDB URL is set in .env")
            return False

        db = get_mongo_db()
        if db is None:
            logger.error("❌ Could not get MongoDB database instance")
            return False

        # Create phone_configs collection (if it doesn't exist)
        # MongoDB creates collections automatically on first insert, but we can create it explicitly
        try:
            # Check if collection exists
            collections = await db.list_collection_names()
            if "phone_configs" not in collections:
                logger.info("Creating phone_configs collection...")
                await db.create_collection("phone_configs")
                logger.info("✅ Collection created")
            else:
                logger.info("✅ phone_configs collection already exists")
        except Exception as e:
            logger.warning(f"Collection creation note: {e}")

        # Ensure indexes exist
        try:
            await db.phone_configs.create_index("phone_number", unique=True)
            logger.info("✅ Unique index on phone_number created")
        except Exception as e:
            logger.warning(f"Index creation (may already exist): {e}")

        try:
            await db.phone_configs.create_index("is_active")
            logger.info("✅ Index on is_active created")
        except Exception as e:
            logger.warning(f"Index creation (may already exist): {e}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ MongoDB setup complete!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("You can now:")
        logger.info("  1. Create phone configs via POST /admin/phone-config")
        logger.info("  2. List configs via GET /admin/phone-configs")
        logger.info("  3. Calls to configured numbers will use their specific settings")
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ MongoDB setup failed: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(setup_mongodb())
    sys.exit(0 if result else 1)
