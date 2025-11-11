"""
MongoDB Database Module for Conversation Storage
Handles MongoDB connection and conversation persistence
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Global MongoDB client and database
_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db = None
_mongo_available = False

def initialize_mongodb():
    """Initialize MongoDB connection"""
    global _mongo_client, _mongo_db, _mongo_available
    
    try:
        from config import MONGODB_URL, MONGODB_DATABASE
        
        # Create MongoDB client
        _mongo_client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        
        # Get database
        _mongo_db = _mongo_client[MONGODB_DATABASE]
        
        # Test connection synchronously (will be tested async on first use)
        _mongo_available = True  # Assume available, will fail gracefully if not
        
        logger.info(f"MongoDB connection initialized successfully (database: {MONGODB_DATABASE})")
        return True
        
    except Exception as e:
        logger.warning(f"MongoDB initialization failed: {e}. Running without MongoDB persistence.")
        _mongo_available = False
        return False

async def test_connection():
    """Test MongoDB connection asynchronously"""
    global _mongo_client, _mongo_available
    if _mongo_client is None:
        _mongo_available = False
        return False
    try:
        await _mongo_client.admin.command('ping')
        _mongo_available = True
        logger.info("MongoDB connection test successful")
        return True
    except Exception as e:
        logger.warning(f"MongoDB connection test failed: {e}")
        _mongo_available = False
        return False

def get_mongo_db():
    """Get MongoDB database instance"""
    if not _mongo_available or _mongo_db is None:
        return None
    return _mongo_db

def is_mongodb_available():
    """Check if MongoDB is available"""
    return _mongo_available

async def close_mongodb():
    """Close MongoDB connection"""
    global _mongo_client, _mongo_available
    if _mongo_client:
        _mongo_client.close()
        _mongo_available = False
        logger.info("MongoDB connection closed")

