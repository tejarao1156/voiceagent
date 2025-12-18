"""
MongoDB AI Chat Store
Handles storing and retrieving AI chat sessions (browser-based voice chat)
Adapted from mongodb_call_store.py pattern
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)


class MongoDBChatStore:
    """Store and retrieve AI chat sessions from MongoDB"""
    
    def __init__(self):
        self.collection_name = "ai_chat"
    
    def _get_collection(self):
        """Get MongoDB collection - creates collection if it doesn't exist"""
        db = get_mongo_db()
        if db is None:
            logger.warning(f"MongoDB database not available, cannot get collection '{self.collection_name}'")
            return None
        try:
            collection = db[self.collection_name]
            logger.debug(f"Accessed MongoDB collection '{self.collection_name}'")
            return collection
        except Exception as e:
            logger.error(f"Error accessing collection '{self.collection_name}': {e}", exc_info=True)
            return None
    
    async def create_session(
        self,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Create a new AI chat session
        
        Args:
            session_id: Optional session ID (generated if not provided)
            config: AI model configuration (stt_model, tts_model, tts_voice, inference_model, provider)
        
        Returns:
            session_id if successful, None otherwise
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping session creation")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Check if session already exists
            existing = await collection.find_one({"session_id": session_id})
            if existing:
                logger.info(f"ℹ️ AI chat session {session_id} already exists")
                return session_id
            
            now = datetime.utcnow().isoformat()
            
            session_doc = {
                "session_id": session_id,
                "config": config or {
                    "stt_model": "whisper-1",
                    "tts_model": "tts-1",
                    "tts_voice": "alloy",
                    "inference_model": "gpt-4o-mini",
                    "provider": "openai"
                },
                "messages": [],  # Array of {role, text, timestamp}
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "ended_at": None
            }
            
            await collection.insert_one(session_doc)
            logger.info(f"✅ Created AI chat session: {session_id}")
            return session_id
            
        except Exception as e:
            if "duplicate" in str(e).lower() or "E11000" in str(e):
                logger.info(f"ℹ️ AI chat session {session_id} already exists (duplicate key)")
                return session_id
            logger.error(f"Error creating AI chat session: {e}", exc_info=True)
            return None
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        text: str
    ) -> bool:
        """Add a message to the chat session
        
        Args:
            session_id: Session ID
            role: "user" or "assistant"
            text: Message text
        
        Returns:
            True if successful
        """
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            timestamp = datetime.utcnow().isoformat()
            message_entry = {
                "role": role,
                "text": text,
                "timestamp": timestamp
            }
            
            result = await collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": message_entry},
                    "$set": {"updated_at": timestamp}
                }
            )
            
            if result.modified_count > 0:
                logger.debug(f"Added message to session {session_id}: {role} - {text[:50]}...")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error adding message to session: {e}")
            return False
    
    async def end_session(self, session_id: str) -> bool:
        """Mark a chat session as ended
        
        Args:
            session_id: Session ID
        
        Returns:
            True if successful
        """
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            now = datetime.utcnow().isoformat()
            
            result = await collection.update_one(
                {"session_id": session_id, "status": "active"},
                {
                    "$set": {
                        "status": "ended",
                        "ended_at": now,
                        "updated_at": now
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Ended AI chat session: {session_id}")
                return True
            
            # Check if already ended
            doc = await collection.find_one({"session_id": session_id})
            if doc and doc.get("status") == "ended":
                logger.info(f"ℹ️ Session {session_id} already ended")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chat session with all messages
        
        Args:
            session_id: Session ID
        
        Returns:
            Session data or None
        """
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            doc = await collection.find_one({"session_id": session_id})
            if doc is None:
                return None
            
            if "_id" in doc:
                del doc["_id"]
            
            return {
                "id": doc.get("session_id"),
                "session_id": doc.get("session_id"),
                "config": doc.get("config", {}),
                "messages": doc.get("messages", []),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
                "ended_at": doc.get("ended_at")
            }
            
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    async def get_all_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all chat sessions for the logs view
        
        Args:
            status: Optional status filter ("active" or "ended")
            limit: Max sessions to return
        
        Returns:
            List of sessions
        """
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            query = {}
            if status:
                query["status"] = status
            
            cursor = collection.find(query).sort("created_at", -1).limit(limit)
            sessions = []
            
            async for doc in cursor:
                if "_id" in doc:
                    del doc["_id"]
                
                messages = doc.get("messages", [])
                
                sessions.append({
                    "id": doc.get("session_id"),
                    "session_id": doc.get("session_id"),
                    "config": doc.get("config", {}),
                    "message_count": len(messages),
                    "last_message": messages[-1].get("text", "")[:50] if messages else "",
                    "status": doc.get("status"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                    "ended_at": doc.get("ended_at")
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session
        
        Args:
            session_id: Session ID
        
        Returns:
            True if successful
        """
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            result = await collection.delete_one({"session_id": session_id})
            
            if result.deleted_count > 0:
                logger.info(f"🗑️ Deleted AI chat session: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False
