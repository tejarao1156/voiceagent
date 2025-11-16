"""
MongoDB Message Store
Handles storing and retrieving SMS/text messages with conversation history
Uses UUID for conversation_id to group messages in conversations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

class MongoDBMessageStore:
    """Store and retrieve SMS/text messages from MongoDB"""
    
    def __init__(self):
        self.collection_name = "messages"
    
    def _get_collection(self):
        """Get MongoDB collection - creates collection if it doesn't exist"""
        db = get_mongo_db()
        if db is None:
            return None
        # Accessing the collection will create it if it doesn't exist
        collection = db[self.collection_name]
        return collection
    
    async def get_or_create_conversation_id(self, from_number: str, to_number: str, agent_id: str) -> Optional[str]:
        """Get existing conversation_id or create a new one with UUID"""
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            # Normalize phone numbers for lookup
            normalized_from = from_number.strip()
            normalized_to = to_number.strip()
            
            # Look for existing conversation between these two numbers for this agent
            # Find the most recent message in a conversation between these numbers
            existing_message = await collection.find_one(
                {
                    "$or": [
                        {"from_number": normalized_from, "to_number": normalized_to, "agent_id": agent_id},
                        {"from_number": normalized_to, "to_number": normalized_from, "agent_id": agent_id}
                    ]
                },
                sort=[("timestamp", -1)]
            )
            
            if existing_message and existing_message.get("conversation_id"):
                conversation_id = existing_message.get("conversation_id")
                logger.info(f"Found existing conversation_id: {conversation_id} for {normalized_from} <-> {normalized_to}")
                return conversation_id
            
            # No existing conversation found, create new UUID
            new_conversation_id = str(uuid.uuid4())
            logger.info(f"Created new conversation_id: {new_conversation_id} for {normalized_from} <-> {normalized_to}")
            return new_conversation_id
            
        except Exception as e:
            logger.error(f"Error getting or creating conversation_id: {e}")
            return None
    
    async def create_message(self, message_sid: str, from_number: str, to_number: str, 
                            body: str, agent_id: Optional[str] = None, 
                            conversation_id: Optional[str] = None) -> bool:
        """Create a new message record when message is received"""
        if not is_mongodb_available():
            logger.error("MongoDB not available, skipping message creation")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.error("Failed to get MongoDB collection 'messages'")
                return False
            
            logger.info(f"📦 Collection 'messages' accessed/created successfully")
            
            now = datetime.utcnow().isoformat()
            agent_id = agent_id or to_number
            
            # Get or create conversation_id if not provided
            if not conversation_id:
                logger.info(f"🔍 Getting or creating conversation_id for {from_number} <-> {to_number} (agent: {agent_id})")
                conversation_id = await self.get_or_create_conversation_id(from_number, to_number, agent_id)
                if not conversation_id:
                    logger.error(f"❌ Could not get or create conversation_id for message {message_sid}")
                    return False
                logger.info(f"✅ Conversation ID: {conversation_id}")
            
            message_doc = {
                "message_sid": message_sid,
                "from_number": from_number,
                "to_number": to_number,
                "body": body,
                "agent_id": agent_id,
                "conversation_id": conversation_id,
                "direction": "inbound",  # Inbound from user
                "status": "received",
                "timestamp": now,
                "created_at": now,
                "updated_at": now,
            }
            
            logger.info(f"💾 Inserting message document into MongoDB collection 'messages'...")
            result = await collection.insert_one(message_doc)
            logger.info(f"✅ Created message record: {message_sid} from {from_number} to {to_number} (conversation_id: {conversation_id}, inserted_id: {result.inserted_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating message record: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False
    
    async def create_outbound_message(self, message_sid: str, from_number: str, to_number: str,
                                     body: str, agent_id: Optional[str] = None,
                                     conversation_id: Optional[str] = None) -> bool:
        """Create a new outbound message record (message sent by agent)"""
        if not is_mongodb_available():
            logger.error("MongoDB not available, skipping outbound message creation")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.error("Failed to get MongoDB collection 'messages'")
                return False
            
            now = datetime.utcnow().isoformat()
            agent_id = agent_id or from_number
            
            # Get or create conversation_id if not provided
            if not conversation_id:
                logger.info(f"🔍 Getting or creating conversation_id for outbound message {from_number} -> {to_number} (agent: {agent_id})")
                # For outbound, we need to find conversation where from_number is the agent and to_number is the user
                conversation_id = await self.get_or_create_conversation_id(to_number, from_number, agent_id)
                if not conversation_id:
                    logger.error(f"❌ Could not get or create conversation_id for outbound message {message_sid}")
                    return False
                logger.info(f"✅ Conversation ID: {conversation_id}")
            
            message_doc = {
                "message_sid": message_sid,
                "from_number": from_number,
                "to_number": to_number,
                "body": body,
                "agent_id": agent_id,
                "conversation_id": conversation_id,
                "direction": "outbound",  # Outbound from agent
                "status": "sent",
                "timestamp": now,
                "created_at": now,
                "updated_at": now,
            }
            
            logger.info(f"💾 Inserting outbound message document into MongoDB collection 'messages'...")
            result = await collection.insert_one(message_doc)
            logger.info(f"✅ Created outbound message record: {message_sid} from {from_number} to {to_number} (conversation_id: {conversation_id}, inserted_id: {result.inserted_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating outbound message record: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False
    
    async def get_conversation_id(self, from_number: str, to_number: str, agent_id: str) -> Optional[str]:
        """Get existing conversation_id for two phone numbers"""
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            # Look for existing conversation between these two numbers for this agent
            existing_message = await collection.find_one(
                {
                    "$or": [
                        {"from_number": from_number.strip(), "to_number": to_number.strip(), "agent_id": agent_id},
                        {"from_number": to_number.strip(), "to_number": from_number.strip(), "agent_id": agent_id}
                    ]
                },
                sort=[("timestamp", -1)]
            )
            
            if existing_message and existing_message.get("conversation_id"):
                return existing_message.get("conversation_id")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting conversation_id: {e}")
            return None
    
    async def get_conversation_history(self, from_number: str, to_number: str, 
                                      agent_id: Optional[str] = None,
                                      limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history between two phone numbers for personalization"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Get conversation_id first
            if not agent_id:
                agent_id = to_number
            
            conversation_id = await self.get_conversation_id(from_number, to_number, agent_id)
            
            if not conversation_id:
                logger.info(f"No existing conversation found for {from_number} <-> {to_number}")
                return []
            
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
    
    async def get_conversations(self, agent_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all conversations grouped by conversation_id with latest message info"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Build query
            query = {}
            if agent_id:
                query["agent_id"] = agent_id
            
            # Aggregate to get latest message per conversation
            pipeline = [
                {"$match": query} if query else {"$match": {}},
                {"$sort": {"timestamp": -1}},
                {
                    "$group": {
                        "_id": "$conversation_id",
                        "conversation_id": {"$first": "$conversation_id"},
                        "agent_id": {"$first": "$agent_id"},
                        "from_number": {"$first": "$from_number"},
                        "to_number": {"$first": "$to_number"},
                        "latest_message": {"$first": "$body"},
                        "latest_timestamp": {"$first": "$timestamp"},
                        "message_count": {"$sum": 1}
                    }
                },
                {"$sort": {"latest_timestamp": -1}},
                {"$limit": limit}
            ]
            
            # Fix pipeline - $match needs to be a dict, not empty
            if not query:
                pipeline[0] = {"$match": {}}
            else:
                pipeline[0] = {"$match": query}
            
            conversations = []
            conversation_count = 0
            async for doc in collection.aggregate(pipeline):
                conversation_id = doc.get("conversation_id")
                if not conversation_id:
                    logger.warning(f"⚠️  Found document without conversation_id, skipping")
                    continue
                
                conversation_count += 1
                logger.info(f"📝 Processing conversation {conversation_count}: {conversation_id}")
                
                # Get all messages in this conversation for the conversation array
                messages_cursor = collection.find(
                    {"conversation_id": conversation_id}
                ).sort("timestamp", 1)
                
                conversation_messages = []
                async for msg_doc in messages_cursor:
                    conversation_messages.append({
                        "role": "user" if msg_doc.get("direction") == "inbound" else "assistant",
                        "text": msg_doc.get("body", ""),
                        "timestamp": msg_doc.get("timestamp")
                    })
                
                # Determine caller and agent numbers correctly
                # For inbound: from_number is user, to_number is agent
                # For outbound: from_number is agent, to_number is user
                # We need to find which number is the user (caller) and which is the agent
                first_msg = await collection.find_one({"conversation_id": conversation_id}, sort=[("timestamp", 1)])
                if first_msg:
                    # If first message is inbound, from_number is caller, to_number is agent
                    if first_msg.get("direction") == "inbound":
                        caller_number = first_msg.get("from_number")
                        agent_number = first_msg.get("to_number")
                    else:
                        # If first message is outbound, to_number is caller, from_number is agent
                        caller_number = first_msg.get("to_number")
                        agent_number = first_msg.get("from_number")
                else:
                    # Fallback to aggregation result
                    caller_number = doc.get("from_number")
                    agent_number = doc.get("to_number")
                
                conversations.append({
                    "id": conversation_id,
                    "conversation_id": conversation_id,
                    "phoneNumberId": doc.get("agent_id"),
                    "callerNumber": caller_number,  # User's number
                    "agentNumber": agent_number,  # Agent's number
                    "status": "active",  # Messages are always "active" (ongoing conversations)
                    "timestamp": doc.get("latest_timestamp"),
                    "latest_message": doc.get("latest_message", ""),
                    "message_count": doc.get("message_count", 0),
                    "conversation": conversation_messages
                })
            
            logger.info(f"✅ Retrieved {len(conversations)} conversation(s) from get_conversations")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error getting conversations: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return []

