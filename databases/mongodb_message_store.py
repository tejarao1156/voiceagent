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
            logger.warning(f"MongoDB database not available, cannot get collection '{self.collection_name}'")
            return None
        # Accessing the collection will create it if it doesn't exist (MongoDB auto-creates)
        try:
            collection = db[self.collection_name]
            logger.debug(f"Accessed MongoDB collection '{self.collection_name}'")
            return collection
        except Exception as e:
            logger.error(f"Error accessing collection '{self.collection_name}': {e}", exc_info=True)
            return None
    
    async def get_or_create_conversation_id(self, from_number: str, to_number: str, agent_id: str) -> Optional[str]:
        """Get existing conversation_id or create a new one with UUID"""
        if not is_mongodb_available():
            return None
        
        try:
            # First try to get existing conversation_id
            existing_id = await self.get_conversation_id(from_number, to_number, agent_id)
            if existing_id:
                return existing_id
            
            # No existing conversation found, create new UUID
            new_conversation_id = str(uuid.uuid4())
            normalized_from = from_number.strip()
            normalized_to = to_number.strip()
            logger.info(f"Created new conversation_id: {new_conversation_id} for {normalized_from} <-> {normalized_to}")
            return new_conversation_id
            
        except Exception as e:
            logger.error(f"Error getting or creating conversation_id: {e}")
            return None
    
    async def check_message_exists(self, message_sid: str, agent_id: str) -> bool:
        """Check if a message with the given message_sid already exists for this agent_id"""
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            # Check if message_sid exists in the messages array for this agent_id
            existing = await collection.find_one({
                "agent_id": agent_id,
                "messages.message_sid": message_sid
            })
            return existing is not None
            
        except Exception as e:
            logger.error(f"Error checking message existence: {e}")
            return False
    
    async def create_message(self, message_sid: str, from_number: str, to_number: str, 
                            body: str, agent_id: Optional[str] = None, 
                            conversation_id: Optional[str] = None) -> bool:
        """Add a new message to the agent's message document (one document per phone number)"""
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
            
            # Check for duplicate message_sid
            if await self.check_message_exists(message_sid, agent_id):
                logger.warning(f"⚠️ Message with message_sid {message_sid} already exists for agent_id {agent_id}, skipping duplicate")
                return False
            
            # Get or create conversation_id if not provided
            if not conversation_id:
                logger.info(f"🔍 Getting or creating conversation_id for {from_number} <-> {to_number} (agent: {agent_id})")
                conversation_id = await self.get_or_create_conversation_id(from_number, to_number, agent_id)
                if not conversation_id:
                    logger.error(f"❌ Could not get or create conversation_id for message {message_sid}")
                    return False
                logger.info(f"✅ Conversation ID: {conversation_id}")
            
            # Create message object
            # For inbound messages: from_number is user, to_number is agent
            message_obj = {
                "message_sid": message_sid,
                "user_number": from_number,  # User sends the message
                "agent_number": to_number,    # Agent receives the message
                "body": body,
                "conversation_id": conversation_id,
                "direction": "inbound",  # Inbound from user
                "role": "user",  # Added role field: inbound = user
                "status": "received",
                "timestamp": now,
            }
            
            # Upsert: Update if document exists, insert if it doesn't
            # One document per agent_id (phone number)
            result = await collection.update_one(
                {"agent_id": agent_id},
                {
                    "$push": {"messages": message_obj},
                    "$set": {
                        "updated_at": now,
                        "agent_id": agent_id  # Ensure agent_id is set
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            
            logger.info(f"✅ Added message {message_sid} to agent_id {agent_id} document (upserted: {result.upserted_id is not None})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating message record: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False
    
    async def create_outbound_message(self, message_sid: str, from_number: str, to_number: str,
                                     body: str, agent_id: Optional[str] = None,
                                     conversation_id: Optional[str] = None) -> bool:
        """Add a new outbound message to the agent's message document (one document per phone number)"""
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
            
            # Check for duplicate message_sid
            if await self.check_message_exists(message_sid, agent_id):
                logger.warning(f"⚠️ Outbound message with message_sid {message_sid} already exists for agent_id {agent_id}, skipping duplicate")
                return False
            
            # Get or create conversation_id if not provided
            if not conversation_id:
                logger.info(f"🔍 Getting or creating conversation_id for outbound message {from_number} -> {to_number} (agent: {agent_id})")
                # For outbound, we need to find conversation where from_number is the agent and to_number is the user
                conversation_id = await self.get_or_create_conversation_id(to_number, from_number, agent_id)
                if not conversation_id:
                    logger.error(f"❌ Could not get or create conversation_id for outbound message {message_sid}")
                    return False
                logger.info(f"✅ Conversation ID: {conversation_id}")
            
            # Create message object
            # For outbound messages: from_number is agent, to_number is user
            message_obj = {
                "message_sid": message_sid,
                "agent_number": from_number,  # Agent sends the message
                "user_number": to_number,     # User receives the message
                "body": body,
                "conversation_id": conversation_id,
                "direction": "outbound",  # Outbound from agent
                "role": "assistant",  # Added role field: outbound = assistant
                "status": "sent",
                "timestamp": now,
            }
            
            # Upsert: Update if document exists, insert if it doesn't
            # One document per agent_id (phone number)
            result = await collection.update_one(
                {"agent_id": agent_id},
                {
                    "$push": {"messages": message_obj},
                    "$set": {
                        "updated_at": now,
                        "agent_id": agent_id  # Ensure agent_id is set
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            
            logger.info(f"✅ Added outbound message {message_sid} to agent_id {agent_id} document (upserted: {result.upserted_id is not None})")
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
            
            # Get the document for this agent_id
            doc = await collection.find_one({"agent_id": agent_id})
            
            if not doc:
                return None
            
            # Look through messages array for existing conversation
            messages_array = doc.get("messages", [])
            
            # Find most recent message between these two numbers
            # Use new format (agent_number/user_number) with backward compatibility
            # from_number parameter = user_number, to_number parameter = agent_number
            normalized_from = from_number.strip()
            normalized_to = to_number.strip()
            
            for msg in reversed(messages_array):  # Check most recent first
                # Use new field names (agent_number/user_number) with backward compatibility
                msg_agent = msg.get("agent_number") or msg.get("from_number", "")
                msg_user = msg.get("user_number") or msg.get("to_number", "")
                
                # Check if this message matches the conversation
                # from_number (parameter) = user, to_number (parameter) = agent
                if msg_agent and msg_user:
                    # Match: (user_number matches from_number AND agent_number matches to_number)
                    # OR reverse (for outbound messages)
                    if ((msg_user == normalized_from and msg_agent == normalized_to) or
                        (msg_agent == normalized_from and msg_user == normalized_to)):
                        conversation_id = msg.get("conversation_id")
                        if conversation_id:
                            return conversation_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting conversation_id: {e}")
            return None
    
    async def get_all_messages_by_agent_id(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all messages for a specific agent_id (phone number) in chronological order"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Get the document for this agent_id (one document per phone number)
            doc = await collection.find_one({"agent_id": agent_id})
            
            if not doc:
                logger.info(f"No messages found for agent_id: {agent_id}")
                return []
            
            # Extract messages array from the document
            messages_array = doc.get("messages", [])
            
            # Sort messages by timestamp (chronological order)
            messages_array.sort(key=lambda x: x.get("timestamp", ""))
            
            # Apply limit
            messages = messages_array[:limit]
            
            # Add agent_id to each message for consistency
            for msg in messages:
                msg["agent_id"] = agent_id
                # Ensure role field exists
                if "role" not in msg:
                    msg["role"] = "user" if msg.get("direction") == "inbound" else "assistant"
            
            logger.info(f"Retrieved {len(messages)} messages for agent_id: {agent_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages by agent_id: {e}")
            return []
    
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
            
            # Get the document for this agent_id
            doc = await collection.find_one({"agent_id": agent_id})
            
            if not doc:
                return []
            
            # Filter messages by conversation_id from the messages array
            messages_array = doc.get("messages", [])
            conversation_messages = [
                msg for msg in messages_array 
                if msg.get("conversation_id") == conversation_id
            ]
            
            # Sort by timestamp
            conversation_messages.sort(key=lambda x: x.get("timestamp", ""))
            
            # Apply limit
            messages = conversation_messages[:limit]
            
            # Ensure role field exists
            for msg in messages:
                if "role" not in msg:
                    msg["role"] = "user" if msg.get("direction") == "inbound" else "assistant"
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def get_all_messages(self, agent_id: Optional[str] = None,
                              conversation_id: Optional[str] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Get all messages with optional filtering
        Works with new structure: one document per phone number with messages array
        """
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Build query - get documents by agent_id (one document per phone number)
            query = {}
            if agent_id:
                query["agent_id"] = agent_id
            
            messages = []
            
            # Get all documents matching the query
            cursor = collection.find(query)
            async for doc in cursor:
                agent_id_doc = doc.get("agent_id")
                messages_array = doc.get("messages", [])
                
                # Filter by conversation_id if specified
                if conversation_id:
                    messages_array = [msg for msg in messages_array if msg.get("conversation_id") == conversation_id]
                
                # Add messages to result
                for msg in messages_array:
                    # Use new field names (agent_number/user_number) with backward compatibility
                    agent_number = msg.get("agent_number") or msg.get("from_number", "")
                    user_number = msg.get("user_number") or msg.get("to_number", "")
                    
                    messages.append({
                        "id": msg.get("message_sid"),
                        "message_sid": msg.get("message_sid"),
                        "agent_number": agent_number,
                        "user_number": user_number,
                        "body": msg.get("body"),
                        "agent_id": agent_id_doc,
                        "conversation_id": msg.get("conversation_id"),
                        "direction": msg.get("direction"),
                        "status": msg.get("status"),
                        "timestamp": msg.get("timestamp"),
                        "role": msg.get("role") or ("user" if msg.get("direction") == "inbound" else "assistant"),
                    })
            
            # Sort by timestamp (most recent first) and apply limit
            messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            messages = messages[:limit]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    async def get_conversations(self, agent_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all conversations grouped by conversation_id with latest message info
        Works with new structure: one document per phone number with messages array
        """
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Build query - get documents by agent_id (one document per phone number)
            query = {}
            if agent_id:
                query["agent_id"] = agent_id
            
            # Get all documents matching the query (one per phone number)
            cursor = collection.find(query)
            all_conversations = {}
            
            async for doc in cursor:
                agent_id_doc = doc.get("agent_id")
                if not agent_id_doc:
                    continue
                
                messages_array = doc.get("messages", [])
                if not messages_array:
                    continue
                
                # Group messages by conversation_id
                conversations_by_id = {}
                for msg in messages_array:
                    conv_id = msg.get("conversation_id")
                    if not conv_id:
                        continue
                    
                    if conv_id not in conversations_by_id:
                        conversations_by_id[conv_id] = {
                            "conversation_id": conv_id,
                            "messages": [],
                            "latest_timestamp": "",
                            "latest_message": "",
                            "first_message": None
                        }
                    
                    conversations_by_id[conv_id]["messages"].append(msg)
                    
                    # Track latest message
                    msg_timestamp = msg.get("timestamp", "")
                    if msg_timestamp > conversations_by_id[conv_id]["latest_timestamp"]:
                        conversations_by_id[conv_id]["latest_timestamp"] = msg_timestamp
                        conversations_by_id[conv_id]["latest_message"] = msg.get("body", "")
                    
                    # Track first message for caller/agent number determination
                    if not conversations_by_id[conv_id]["first_message"]:
                        conversations_by_id[conv_id]["first_message"] = msg
                
                # Convert to conversation format
                for conv_id, conv_data in conversations_by_id.items():
                    # Sort messages by timestamp
                    conv_data["messages"].sort(key=lambda x: x.get("timestamp", ""))
                    
                    # Build conversation array for UI
                    conversation_messages = []
                    for msg in conv_data["messages"]:
                        conversation_messages.append({
                            "role": msg.get("role") or ("user" if msg.get("direction") == "inbound" else "assistant"),
                            "text": msg.get("body", ""),
                            "timestamp": msg.get("timestamp")
                        })
                    
                    # Determine caller and agent numbers from messages
                    # Find the first inbound message to determine the caller (user who initiated conversation)
                    first_inbound_msg = None
                    for msg in conv_data["messages"]:
                        if msg.get("direction") == "inbound":
                            first_inbound_msg = msg
                            break
                    
                    # If no inbound message found, use first message (outbound)
                    if not first_inbound_msg:
                        first_inbound_msg = conv_data["first_message"]
                    
                    if first_inbound_msg:
                        # Use new field names (agent_number/user_number) with backward compatibility
                        msg_agent_number = first_inbound_msg.get("agent_number") or first_inbound_msg.get("from_number", "")
                        msg_user_number = first_inbound_msg.get("user_number") or first_inbound_msg.get("to_number", "")
                        
                        if first_inbound_msg.get("direction") == "inbound":
                            # Inbound: user sends to agent
                            caller_number = msg_user_number  # User is the caller
                            agent_number = msg_agent_number  # Agent receives
                        else:
                            # Outbound: agent sends to user (first message is outbound - rare case)
                            caller_number = msg_user_number  # User receives (will be the caller when they respond)
                            agent_number = msg_agent_number  # Agent sends
                    else:
                        caller_number = ""
                        agent_number = agent_id_doc
                    
                    # Store conversation (use conversation_id as key to avoid duplicates)
                    if conv_id not in all_conversations:
                        all_conversations[conv_id] = {
                            "id": conv_id,
                            "conversation_id": conv_id,
                            "phoneNumberId": agent_id_doc,
                            "callerNumber": caller_number,
                            "agentNumber": agent_number,
                            "status": "active",
                            "timestamp": conv_data["latest_timestamp"],
                            "latest_message": conv_data["latest_message"],
                            "message_count": len(conv_data["messages"]),
                            "conversation": conversation_messages
                        }
            
            # Convert to list and sort by latest timestamp
            conversations = list(all_conversations.values())
            conversations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Apply limit
            conversations = conversations[:limit]
            
            logger.info(f"✅ Retrieved {len(conversations)} conversation(s) from get_conversations")
            if conversations:
                logger.info(f"   Sample conversation: id={conversations[0].get('conversation_id')}, phoneNumberId={conversations[0].get('phoneNumberId')}, message_count={conversations[0].get('message_count')}")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error getting conversations: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return []

