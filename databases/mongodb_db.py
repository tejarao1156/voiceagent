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
        
        # Check if MongoDB URL is provided
        if not MONGODB_URL or MONGODB_URL.strip() == "":
            logger.warning("MongoDB URL is not set. Set MONGODB_URL in .env file to enable MongoDB.")
            _mongo_available = False
            return False
        
        # Create MongoDB client
        # For mongodb+srv:// URLs, TLS is automatically enabled by MongoDB
        # Increase timeout for better reliability
        # tlsAllowInvalidCertificates=True is needed for macOS SSL certificate issues
        _mongo_client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=10000,  # 10 second timeout (increased from 5s)
            tlsAllowInvalidCertificates=True  # Fix for macOS SSL certificate verification
        )
        
        # Get database
        _mongo_db = _mongo_client[MONGODB_DATABASE]
        
        # Test connection synchronously (will be tested async on first use)
        _mongo_available = True  # Assume available, will fail gracefully if not
        
        logger.info(f"MongoDB connection initialized successfully (database: {MONGODB_DATABASE})")
        logger.info(f"MongoDB URL: {MONGODB_URL[:50]}..." if len(MONGODB_URL) > 50 else f"MongoDB URL: {MONGODB_URL}")
        return True
        
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}. Running without MongoDB persistence.", exc_info=True)
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

async def list_collections() -> List[Dict[str, Any]]:
    """List all MongoDB collections with their document counts"""
    global _mongo_db, _mongo_available
    
    if not _mongo_available or _mongo_db is None:
        return []
    
    try:
        collections_info = []
        collection_names = await _mongo_db.list_collection_names()
        
        for collection_name in collection_names:
            collection = _mongo_db[collection_name]
            count = await collection.count_documents({})
            collections_info.append({
                "name": collection_name,
                "document_count": count
            })
        
        # Sort by name
        collections_info.sort(key=lambda x: x["name"])
        
        return collections_info
    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        return []

async def verify_collection_exists(collection_name: str) -> bool:
    """Verify if a MongoDB collection exists"""
    global _mongo_db, _mongo_available
    
    if not _mongo_available or _mongo_db is None:
        return False
    
    try:
        collection_names = await _mongo_db.list_collection_names()
        return collection_name in collection_names
    except Exception as e:
        logger.error(f"Error verifying collection existence: {e}", exc_info=True)
        return False

async def close_mongodb():
    """Close MongoDB connection"""
    global _mongo_client, _mongo_available
    if _mongo_client:
        _mongo_client.close()
        _mongo_available = False
        logger.info("MongoDB connection closed")

