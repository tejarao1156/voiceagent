"""
MongoDB Message Store
Handles storing and retrieving SMS/text messages with conversation history
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

class MongoDBMessageStore:
    """Store and retrieve SMS/text messages from MongoDB"""
    
    def __init__(self):
        self.collection_name = "messages"
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.collection_name]
    
    async def create_message(self, message_sid: str, from_number: str, to_number: str, 
                            body: str, agent_id: Optional[str] = None, 
                            conversation_id: Optional[str] = None) -> bool:
        """Create a new message record when message is received"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping message creation")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            now = datetime.utcnow().isoformat()
            
            # Use conversation_id if provided, otherwise create one based on phone numbers
            if not conversation_id:
                # Create consistent conversation ID from phone numbers (sorted)
                phone_numbers = sorted([from_number, to_number])
                conversation_id = f"conv_{phone_numbers[0]}_{phone_numbers[1]}"
            
            message_doc = {
                "message_sid": message_sid,
                "from_number": from_number,
                "to_number": to_number,
                "body": body,
                "agent_id": agent_id or to_number,
                "conversation_id": conversation_id,
                "direction": "inbound",  # Inbound from user
                "status": "received",
                "timestamp": now,
                "created_at": now,
                "updated_at": now,
            }
            
            await collection.insert_one(message_doc)
            logger.info(f"Created message record: {message_sid} from {from_number} to {to_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating message record: {e}")
            return False
    
    async def create_outbound_message(self, message_sid: str, from_number: str, to_number: str,
                                     body: str, agent_id: Optional[str] = None,
                                     conversation_id: Optional[str] = None) -> bool:
        """Create a new outbound message record (message sent by agent)"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping outbound message creation")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            now = datetime.utcnow().isoformat()
            
            # Use conversation_id if provided, otherwise create one based on phone numbers
            if not conversation_id:
                phone_numbers = sorted([from_number, to_number])
                conversation_id = f"conv_{phone_numbers[0]}_{phone_numbers[1]}"
            
            message_doc = {
                "message_sid": message_sid,
                "from_number": from_number,
                "to_number": to_number,
                "body": body,
                "agent_id": agent_id or from_number,
                "conversation_id": conversation_id,
                "direction": "outbound",  # Outbound from agent
                "status": "sent",
                "timestamp": now,
                "created_at": now,
                "updated_at": now,
            }
            
            await collection.insert_one(message_doc)
            logger.info(f"Created outbound message record: {message_sid} from {from_number} to {to_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating outbound message record: {e}")
            return False
    
    async def get_conversation_history(self, from_number: str, to_number: str, 
                                      limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history between two phone numbers for personalization"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Create conversation ID from phone numbers (sorted)
            phone_numbers = sorted([from_number, to_number])
            conversation_id = f"conv_{phone_numbers[0]}_{phone_numbers[1]}"
            
            # Get all messages in this conversation, ordered by timestamp
            cursor = collection.find(
                {"conversation_id": conversation_id}
            ).sort("timestamp", 1).limit(limit)
            
            messages = []
            async for doc in cursor:
                if "_id" in doc:
                    del doc["_id"]
                
                messages.append({
                    "message_sid": doc.get("message_sid"),
                    "from_number": doc.get("from_number"),
                    "to_number": doc.get("to_number"),
                    "body": doc.get("body"),
                    "direction": doc.get("direction"),  # "inbound" or "outbound"
                    "timestamp": doc.get("timestamp"),
                    "role": "user" if doc.get("direction") == "inbound" else "assistant",
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def get_all_messages(self, agent_id: Optional[str] = None,
                              conversation_id: Optional[str] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Get all messages with optional filtering"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            query = {}
            if agent_id:
                query["agent_id"] = agent_id
            if conversation_id:
                query["conversation_id"] = conversation_id
            
            cursor = collection.find(query).sort("timestamp", -1).limit(limit)
            messages = []
            
            async for doc in cursor:
                if "_id" in doc:
                    del doc["_id"]
                
                messages.append({
                    "id": doc.get("message_sid"),
                    "message_sid": doc.get("message_sid"),
                    "from_number": doc.get("from_number"),
                    "to_number": doc.get("to_number"),
                    "body": doc.get("body"),
                    "agent_id": doc.get("agent_id"),
                    "conversation_id": doc.get("conversation_id"),
                    "direction": doc.get("direction"),
                    "status": doc.get("status"),
                    "timestamp": doc.get("timestamp"),
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

