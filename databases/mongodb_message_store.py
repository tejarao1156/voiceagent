"""
MongoDB Message Store
Handles storing and retrieving SMS/text messages with conversation history
Uses UUID for conversation_id to group messages in conversations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import uuid
from .mongodb_db import get_mongo_db, is_mongodb_available
from .mongodb_phone_store import normalize_phone_number

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
    
    async def get_or_create_conversation_id(self, from_number: str, to_number: str, agent_id: str, 
                                            force_new: bool = False) -> tuple[Optional[str], bool]:
        """Get existing conversation_id or create a new one with UUID.
        
        If the last message is more than 1 day old, creates a new conversation.
        
        Args:
            from_number: User phone number
            to_number: Agent phone number  
            agent_id: Agent ID for lookup
            force_new: If True, forces creation of new conversation
            
        Returns:
            Tuple of (conversation_id, is_new_conversation)
            - conversation_id: UUID for the conversation
            - is_new_conversation: True if this is a new conversation (should send greeting)
        """
        if not is_mongodb_available():
            return None, False
        
        try:
            normalized_from = normalize_phone_number(from_number)
            normalized_agent = normalize_phone_number(agent_id)
            
            # Check last message time to determine greeting and conversation status
            last_msg_time = await self.get_last_message_time(normalized_agent, normalized_from)
            
            if last_msg_time is None:
                # No previous messages - this is a brand new conversation
                new_conversation_id = str(uuid.uuid4())
                logger.info(f"🆕 No previous messages - creating NEW conversation: {new_conversation_id}")
                return new_conversation_id, True  # New conv + greeting
            
            # Calculate time since last message
            time_since_last = datetime.utcnow() - last_msg_time.replace(tzinfo=None)
            minutes_since_last = time_since_last.total_seconds() / 60
            hours_since_last = time_since_last.total_seconds() / 3600
            days_since_last = time_since_last.days
            
            logger.info(f"📅 Time since last message: {minutes_since_last:.1f} minutes ({hours_since_last:.1f} hours, {days_since_last} days)")
            
            if days_since_last >= 1 or force_new:
                # More than 1 day since last message - create NEW conversation + greeting
                new_conversation_id = str(uuid.uuid4())
                logger.info(f"🆕 Last message > 1 day ago - creating NEW conversation: {new_conversation_id}")
                return new_conversation_id, True  # New conv + greeting
            
            # Get existing conversation ID
            existing_id = await self.get_conversation_id(from_number, to_number, agent_id)
            if not existing_id:
                # Fallback - create new if no existing ID found
                new_conversation_id = str(uuid.uuid4())
                logger.info(f"🆕 No existing conversation_id found - creating NEW: {new_conversation_id}")
                return new_conversation_id, True  # New conv + greeting
            
            if minutes_since_last < 30:
                # Less than 30 minutes - active chat, no greeting
                logger.info(f"✅ Active chat (< 30 min) - continuing conversation: {existing_id}, NO greeting")
                return existing_id, False  # Same conv, no greeting
            else:
                # 30 min to 1 day - re-engaging after break, send greeting but same conversation
                logger.info(f"👋 Re-engaging (30 min - 1 day gap) - continuing conversation: {existing_id}, WITH greeting")
                return existing_id, True  # Same conv + greeting
            
        except Exception as e:
            logger.error(f"Error getting or creating conversation_id: {e}")
            return None, False
    
    async def check_message_exists(self, message_sid: str, agent_id: str, user_number: Optional[str] = None) -> bool:
        """Check if a message with the given message_sid already exists for this agent_id + user_number"""
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            # Build query - if user_number provided, use compound key
            query = {"agent_id": agent_id, "messages.message_sid": message_sid}
            if user_number:
                query["user_number"] = user_number
            
            existing = await collection.find_one(query)
            return existing is not None
            
        except Exception as e:
            logger.error(f"Error checking message existence: {e}")
            return False
    
    async def create_message(self, message_sid: str, from_number: str, to_number: str, 
                            body: str, agent_id: Optional[str] = None, 
                            conversation_id: Optional[str] = None,
                            channel: str = "sms") -> bool:
        """Add a new message to the conversation document.
        Document structure: { agent_id, user_number, messages: [...] }
        One document per agent_id + user_number combination."""
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
            normalized_user = normalize_phone_number(from_number)
            normalized_agent = normalize_phone_number(agent_id)
            
            # Check for duplicate message_sid within this conversation
            if await self.check_message_exists(message_sid, normalized_agent, normalized_user):
                logger.warning(f"⚠️ Message with message_sid {message_sid} already exists, skipping duplicate")
                return False
            
            # Check if conversation exists with agent_id + user_number
            conversation_exists = await self.check_conversation_exists(normalized_agent, normalized_user)
            
            if conversation_exists:
                logger.info(f"✅ Found existing conversation for agent_id={normalized_agent}, user_number={normalized_user}")
            else:
                logger.info(f"🆕 Creating new conversation entry for agent_id={normalized_agent}, user_number={normalized_user}")
            
            # Get or create conversation_id if not provided
            if not conversation_id:
                logger.info(f"🔍 Getting or creating conversation_id for {from_number} <-> {to_number} (agent: {normalized_agent})")
                conversation_id, _ = await self.get_or_create_conversation_id(from_number, to_number, normalized_agent)
                if not conversation_id:
                    logger.error(f"❌ Could not get or create conversation_id for message {message_sid}")
                    return False
                logger.info(f"✅ Conversation ID: {conversation_id}")
            
            # Create message object
            # For inbound messages: from_number is user, to_number is agent
            message_obj = {
                "message_sid": message_sid,
                "agent_number": to_number,    # Agent receives the message
                "body": body,
                "conversation_id": conversation_id,
                "direction": "inbound",  # Inbound from user
                "role": "user",  # Added role field: inbound = user
                "status": "received",
                "timestamp": now,
                "channel": channel,  # Track message channel (sms or whatsapp)
            }
            
            # Upsert: Update if document exists, insert if it doesn't
            # One document per agent_id + user_number combination
            result = await collection.update_one(
                {
                    "agent_id": normalized_agent,
                    "user_number": normalized_user
                },
                {
                    "$push": {"messages": message_obj},
                    "$set": {
                        "updated_at": now,
                        "agent_id": normalized_agent,  # Ensure agent_id is set
                        "user_number": normalized_user  # Ensure user_number is set
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            
            logger.info(f"✅ Added message {message_sid} to conversation (agent_id={normalized_agent}, user_number={normalized_user}) (upserted: {result.upserted_id is not None})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating message record: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False
    
    async def create_outbound_message(self, message_sid: str, from_number: str, to_number: str,
                                     body: str, agent_id: Optional[str] = None,
                                     conversation_id: Optional[str] = None,
                                     channel: str = "sms") -> bool:
        """Add a new outbound message to the conversation document.
        Document structure: { agent_id, user_number, messages: [...] }
        One document per agent_id + user_number combination."""
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
            normalized_agent = normalize_phone_number(agent_id)
            normalized_user = normalize_phone_number(to_number)  # to_number is the user for outbound
            
            # Check for duplicate message_sid within this conversation
            if await self.check_message_exists(message_sid, normalized_agent, normalized_user):
                logger.warning(f"⚠️ Outbound message with message_sid {message_sid} already exists, skipping duplicate")
                return False
            
            # Get or create conversation_id if not provided
            if not conversation_id:
                logger.info(f"🔍 Getting or creating conversation_id for outbound message {from_number} -> {to_number} (agent: {normalized_agent})")
                # For outbound, we need to find conversation where from_number is the agent and to_number is the user
                conversation_id, _ = await self.get_or_create_conversation_id(to_number, from_number, normalized_agent)
                if not conversation_id:
                    logger.error(f"❌ Could not get or create conversation_id for outbound message {message_sid}")
                    return False
                logger.info(f"✅ Conversation ID: {conversation_id}")
            
            # Create message object
            # For outbound messages: from_number is agent, to_number is user
            message_obj = {
                "message_sid": message_sid,
                "agent_number": from_number,  # Agent sends the message
                "body": body,
                "conversation_id": conversation_id,
                "direction": "outbound",  # Outbound from agent
                "role": "assistant",  # Added role field: outbound = assistant
                "status": "sent",
                "timestamp": now,
                "channel": channel,  # Track message channel (sms or whatsapp)
            }
            
            # Upsert: Update if document exists, insert if it doesn't
            # One document per agent_id + user_number combination
            result = await collection.update_one(
                {
                    "agent_id": normalized_agent,
                    "user_number": normalized_user
                },
                {
                    "$push": {"messages": message_obj},
                    "$set": {
                        "updated_at": now,
                        "agent_id": normalized_agent,  # Ensure agent_id is set
                        "user_number": normalized_user  # Ensure user_number is set
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            
            logger.info(f"✅ Added outbound message {message_sid} to conversation (agent_id={normalized_agent}, user_number={normalized_user}) (upserted: {result.upserted_id is not None})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating outbound message record: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return False
    
    async def get_conversation_id(self, from_number: str, to_number: str, agent_id: str) -> Optional[str]:
        """Get existing conversation_id for two phone numbers
        from_number = user_number, to_number = agent_number"""
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            # Normalize phone numbers
            normalized_agent = normalize_phone_number(agent_id)
            normalized_user = normalize_phone_number(from_number)  # from_number is user
            
            # Get the document for this agent_id + user_number combination
            doc = await collection.find_one({
                "agent_id": normalized_agent,
                "user_number": normalized_user
            })
            
            if not doc:
                return None
            
            # Get conversation_id from the most recent message
            messages_array = doc.get("messages", [])
            if not messages_array:
                return None
            
            # Get conversation_id from the most recent message
            for msg in reversed(messages_array):  # Check most recent first
                        conversation_id = msg.get("conversation_id")
                        if conversation_id:
                            return conversation_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting conversation_id: {e}")
            return None
    
    async def get_last_message_time(self, agent_id: str, user_number: str) -> Optional[datetime]:
        """Get timestamp of the most recent message between user and agent.
        
        Args:
            agent_id: Normalized agent phone number
            user_number: Normalized user phone number
            
        Returns:
            datetime of last message, or None if no messages exist
        """
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            normalized_agent = normalize_phone_number(agent_id)
            normalized_user = normalize_phone_number(user_number)
            
            # Get the document for this agent_id + user_number combination
            doc = await collection.find_one({
                "agent_id": normalized_agent,
                "user_number": normalized_user
            })
            
            if not doc:
                logger.info(f"📅 No conversation found for agent={normalized_agent}, user={normalized_user}")
                return None
            
            # Get messages array and find the most recent timestamp
            messages_array = doc.get("messages", [])
            if not messages_array:
                logger.info(f"📅 Conversation exists but no messages for agent={normalized_agent}, user={normalized_user}")
                return None
            
            # Find the most recent message timestamp
            latest_time = None
            for msg in messages_array:
                timestamp_str = msg.get("timestamp")
                if timestamp_str:
                    try:
                        msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if latest_time is None or msg_time > latest_time:
                            latest_time = msg_time
                    except Exception as parse_error:
                        logger.warning(f"Could not parse timestamp '{timestamp_str}': {parse_error}")
            
            if latest_time:
                logger.info(f"📅 Last message time for agent={normalized_agent}, user={normalized_user}: {latest_time.isoformat()}")
            
            return latest_time
            
        except Exception as e:
            logger.error(f"Error getting last message time: {e}", exc_info=True)
            return None
    
    async def get_all_messages_by_agent_id(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all messages for a specific agent_id across all user conversations in chronological order"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            normalized_agent = normalize_phone_number(agent_id)
            
            # Get all documents for this agent_id (multiple documents, one per user_number)
            cursor = collection.find({"agent_id": normalized_agent})
            
            all_messages = []
            async for doc in cursor:
                messages_array = doc.get("messages", [])
                user_number = doc.get("user_number", "")
                
                # Add user_number and agent_id to each message
                for msg in messages_array:
                    msg["agent_id"] = normalized_agent
                    msg["user_number"] = user_number  # Add user_number from document level
                    # Ensure role field exists
                    if "role" not in msg:
                        msg["role"] = "user" if msg.get("direction") == "inbound" else "assistant"
                    all_messages.append(msg)
            
            # Sort messages by timestamp (chronological order)
            all_messages.sort(key=lambda x: x.get("timestamp", ""))
            
            # Apply limit
            messages = all_messages[:limit]
            
            logger.info(f"Retrieved {len(messages)} messages for agent_id: {normalized_agent}")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages by agent_id: {e}")
            return []
    
    async def check_conversation_exists(self, agent_id: str, user_number: str) -> bool:
        """Check if a conversation document exists for agent_id + user_number combination"""
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            # Normalize phone numbers
            normalized_agent = normalize_phone_number(agent_id)
            normalized_user = normalize_phone_number(user_number)
            
            # Check if document exists with both agent_id and user_number
            doc = await collection.find_one({
                "agent_id": normalized_agent,
                "user_number": normalized_user
            })
            
            return doc is not None
            
        except Exception as e:
            logger.error(f"Error checking conversation existence: {e}")
            return False
    
    async def get_last_24h_messages(self, agent_id: str, user_number: str) -> List[Dict[str, Any]]:
        """Get messages from the last 24 hours for a specific agent_id + user_number combination"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Normalize phone numbers
            normalized_agent = normalize_phone_number(agent_id)
            normalized_user = normalize_phone_number(user_number)
            
            # Calculate 24 hours ago timestamp
            now = datetime.utcnow()
            twenty_four_hours_ago = now - timedelta(hours=24)
            cutoff_timestamp = twenty_four_hours_ago.isoformat()
            
            logger.info(f"📅 Getting messages from last 24 hours (since {cutoff_timestamp})")
            logger.info(f"   agent_id: {normalized_agent}, user_number: {normalized_user}")
            
            # Get the document for this agent_id + user_number combination
            doc = await collection.find_one({
                "agent_id": normalized_agent,
                "user_number": normalized_user
            })
            
            if not doc:
                logger.info(f"No document found for agent_id={normalized_agent}, user_number={normalized_user}")
                return []
            
            # Filter messages by timestamp (last 24 hours)
            messages_array = doc.get("messages", [])
            
            last_24h_messages = []
            for msg in messages_array:
                msg_timestamp = msg.get("timestamp", "")
                
                # Check if message is within last 24 hours
                if msg_timestamp >= cutoff_timestamp:
                    # Ensure role field exists
                    if "role" not in msg:
                        msg["role"] = "user" if msg.get("direction") == "inbound" else "assistant"
                    last_24h_messages.append(msg)
            
            # Sort by timestamp (oldest first)
            last_24h_messages.sort(key=lambda x: x.get("timestamp", ""))
            
            logger.info(f"📅 Found {len(last_24h_messages)} message(s) from last 24 hours")
            
            return last_24h_messages
            
        except Exception as e:
            logger.error(f"Error getting last 24h messages: {e}", exc_info=True)
            return []
    
    async def get_conversation_history(self, from_number: str, to_number: str, 
                                      agent_id: Optional[str] = None,
                                      limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history between two phone numbers for personalization
        Now returns last 24 hours of messages for LLM inference"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Get conversation_id first
            if not agent_id:
                agent_id = to_number
            
            # Use the new method to get last 24 hours of messages
            messages = await self.get_last_24h_messages(agent_id, from_number)
            
            # Apply limit if needed
            if limit and len(messages) > limit:
                messages = messages[-limit:]  # Get most recent messages
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def get_all_messages(self, agent_id: Optional[str] = None,
                              conversation_id: Optional[str] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Get all messages with optional filtering
        Works with new structure: one document per agent_id + user_number combination
        """
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Build query - get documents by agent_id (normalize if provided)
            query = {}
            if agent_id:
                query["agent_id"] = normalize_phone_number(agent_id)
            
            messages = []
            
            # Get all documents matching the query (one per agent_id + user_number)
            cursor = collection.find(query)
            async for doc in cursor:
                agent_id_doc = doc.get("agent_id")
                user_number_doc = doc.get("user_number")  # Get from document level
                messages_array = doc.get("messages", [])
                
                # Filter by conversation_id if specified
                if conversation_id:
                    messages_array = [msg for msg in messages_array if msg.get("conversation_id") == conversation_id]
                
                # Add messages to result
                for msg in messages_array:
                    agent_number = msg.get("agent_number") or agent_id_doc
                    
                    messages.append({
                        "id": msg.get("message_sid"),
                        "message_sid": msg.get("message_sid"),
                        "agent_number": agent_number,
                        "user_number": user_number_doc,  # From document level
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
        """Get all conversations grouped by agent_id + user_number
        Works with new structure: one document per agent_id + user_number combination
        """
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Build query - get documents by agent_id (normalize if provided)
            query = {}
            if agent_id:
                query["agent_id"] = normalize_phone_number(agent_id)
            
            # Get all documents matching the query (one per agent_id + user_number)
            cursor = collection.find(query)
            all_conversations = {}
            
            async for doc in cursor:
                agent_id_doc = doc.get("agent_id")
                user_number_doc = doc.get("user_number")
                
                if not agent_id_doc or not user_number_doc:
                    continue
                
                messages_array = doc.get("messages", [])
                if not messages_array:
                    continue
                
                # Sort messages by timestamp
                messages_array.sort(key=lambda x: x.get("timestamp", ""))
                
                # Get conversation_id from most recent message
                conversation_id = None
                for msg in reversed(messages_array):
                    if msg.get("conversation_id"):
                        conversation_id = msg.get("conversation_id")
                        break
                
                if not conversation_id:
                    conversation_id = str(uuid.uuid4())
                
                # Get latest message info
                latest_message_obj = messages_array[-1] if messages_array else None
                latest_timestamp = latest_message_obj.get("timestamp", "") if latest_message_obj else ""
                latest_message = latest_message_obj.get("body", "") if latest_message_obj else ""
                
                # Build conversation array for UI
                conversation_messages = []
                for msg in messages_array:
                    # Get or infer direction field (for backward compatibility with old messages)
                    direction = msg.get("direction")
                    if not direction:
                        # Infer direction from role field if direction is missing
                        role = msg.get("role")
                        if role == "user" or role == "customer":
                            direction = "inbound"
                        else:
                            direction = "outbound"
                    
                    # Determine role (with direction fallback)
                    role = msg.get("role") or ("user" if direction == "inbound" else "assistant")
                    
                    conversation_messages.append({
                        "role": role,
                        "direction": direction,  # Always include direction for UI to use
                        "text": msg.get("body", ""),
                        "timestamp": msg.get("timestamp")
                    })
                
                # Store conversation
                # Use composite ID to ensure uniqueness: agent_id + user_number
                unique_id = f"{agent_id_doc}_{user_number_doc}"
                
                if unique_id not in all_conversations:
                    all_conversations[unique_id] = {
                        "id": unique_id,
                        "conversation_id": conversation_id,
                        "phoneNumberId": agent_id_doc,
                        "callerNumber": user_number_doc,
                        "agentNumber": agent_id_doc,
                        "status": "active",
                        "timestamp": latest_timestamp,
                        "latest_message": latest_message,
                        "message_count": len(messages_array),
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
    
    async def get_conversations_for_user(
        self, 
        user_phone_numbers: List[str],
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get conversations filtered by user's phone numbers for multi-tenancy
        
        Args:
            user_phone_numbers: List of phone numbers owned by the user
            agent_id: Optional filter for specific phone number (must be in user_phone_numbers)
            limit: Max conversations to return
        
        Returns:
            List of conversations belonging to the user
        """
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Normalize all user phone numbers
            normalized_numbers = [normalize_phone_number(pn) for pn in user_phone_numbers]
            
            # Build query - filter by user's phone numbers
            if agent_id:
                # Single phone number filter (already validated as belonging to user)
                query = {"agent_id": normalize_phone_number(agent_id)}
            else:
                # Filter by all user's phone numbers
                query = {"agent_id": {"$in": normalized_numbers}}
            
            # Get all documents matching the query
            cursor = collection.find(query)
            all_conversations = {}
            
            async for doc in cursor:
                agent_id_doc = doc.get("agent_id")
                user_number_doc = doc.get("user_number")
                
                if not agent_id_doc or not user_number_doc:
                    continue
                
                messages_array = doc.get("messages", [])
                if not messages_array:
                    continue
                
                # Sort messages by timestamp
                messages_array.sort(key=lambda x: x.get("timestamp", ""))
                
                # Get conversation_id from most recent message
                conversation_id = None
                for msg in reversed(messages_array):
                    if msg.get("conversation_id"):
                        conversation_id = msg.get("conversation_id")
                        break
                
                if not conversation_id:
                    conversation_id = str(uuid.uuid4())
                
                # Get latest message info
                latest_message_obj = messages_array[-1] if messages_array else None
                latest_timestamp = latest_message_obj.get("timestamp", "") if latest_message_obj else ""
                latest_message = latest_message_obj.get("body", "") if latest_message_obj else ""
                
                # Build conversation array for UI
                conversation_messages = []
                for msg in messages_array:
                    # Get or infer direction field
                    direction = msg.get("direction")
                    if not direction:
                        role = msg.get("role")
                        if role == "user" or role == "customer":
                            direction = "inbound"
                        else:
                            direction = "outbound"
                    
                    # Determine role (with direction fallback)
                    role = msg.get("role") or ("user" if direction == "inbound" else "assistant")
                    
                    conversation_messages.append({
                        "role": role,
                        "direction": direction,
                        "text": msg.get("body", ""),
                        "timestamp": msg.get("timestamp")
                    })
                
                # Store conversation
                unique_id = f"{agent_id_doc}_{user_number_doc}"
                
                if unique_id not in all_conversations:
                    all_conversations[unique_id] = {
                        "id": unique_id,
                        "conversation_id": conversation_id,
                        "phoneNumberId": agent_id_doc,
                        "callerNumber": user_number_doc,
                        "agentNumber": agent_id_doc,
                        "status": "active",
                        "timestamp": latest_timestamp,
                        "latest_message": latest_message,
                        "message_count": len(messages_array),
                        "conversation": conversation_messages
                    }
            
            # Convert to list and sort by latest timestamp
            conversations = list(all_conversations.values())
            conversations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Apply limit
            conversations = conversations[:limit]
            
            logger.info(f"✅ Retrieved {len(conversations)} conversation(s) for user (filtered by {len(normalized_numbers)} phone(s))")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error getting conversations for user: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return []

