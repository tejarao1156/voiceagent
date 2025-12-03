"""
MongoDB Conversation Store
Handles saving and loading conversations from MongoDB
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available
from .mongodb_models import ConversationSession, ConversationMessage, conversation_to_dict, dict_to_conversation
from config import MONGODB_CONVERSATIONS_COLLECTION

logger = logging.getLogger(__name__)

class MongoDBConversationStore:
    """Store and retrieve conversations from MongoDB"""
    
    def __init__(self):
        self.collection_name = MONGODB_CONVERSATIONS_COLLECTION
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.collection_name]
    
    async def save_session(self, session_id: str, session_data: Dict[str, Any], 
                          agent_id: Optional[str] = None) -> bool:
        """Save or update a conversation session"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping save")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            # Convert session_data to MongoDB format
            conversation = ConversationSession(
                session_id=session_id,
                customer_id=session_data.get("customer_id"),
                agent_id=agent_id,
                persona=session_data.get("persona"),
                status=session_data.get("status", "active"),
                state=session_data.get("state"),
                messages=self._convert_history_to_messages(session_data.get("conversation_history", [])),
                metadata={
                    "order_items": session_data.get("order_items", []),
                    "customer_info": session_data.get("customer_info", {}),
                },
                created_at=session_data.get("created_at", datetime.utcnow().isoformat()),
                updated_at=datetime.utcnow().isoformat(),
            )
            
            # Upsert conversation
            await collection.update_one(
                {"session_id": session_id},
                {"$set": conversation_to_dict(conversation)},
                upsert=True
            )
            
            logger.debug(f"Saved conversation session {session_id} to MongoDB")
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation to MongoDB: {e}")
            return False
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a conversation session from MongoDB"""
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            doc = await collection.find_one({"session_id": session_id})
            if doc is None:
                return None
            
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            conversation = dict_to_conversation(doc)
            
            # Convert back to session_data format
            session_data = {
                "session_id": conversation.session_id,
                "customer_id": conversation.customer_id,
                "persona": conversation.persona,
                "status": conversation.status,
                "state": conversation.state,
                "conversation_history": self._convert_messages_to_history(conversation.messages),
                "order_items": conversation.metadata.get("order_items", []),
                "customer_info": conversation.metadata.get("customer_info", {}),
                "created_at": conversation.created_at,
                "last_activity": conversation.updated_at,
            }
            
            logger.debug(f"Loaded conversation session {session_id} from MongoDB")
            return session_data
            
        except Exception as e:
            logger.error(f"Error loading conversation from MongoDB: {e}")
            return None
    
    async def add_message(self, session_id: str, user_input: str, agent_response: str) -> bool:
        """Add a message to an existing conversation"""
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            timestamp = datetime.utcnow().isoformat()
            
            # Add user message
            user_msg = ConversationMessage(
                timestamp=timestamp,
                role="user",
                content=user_input
            )
            
            # Add assistant message
            assistant_msg = ConversationMessage(
                timestamp=timestamp,
                role="assistant",
                content=agent_response
            )
            
            # Update conversation with new messages
            await collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {
                        "messages": {
                            "$each": [user_msg.dict(), assistant_msg.dict()]
                        }
                    },
                    "$set": {
                        "updated_at": timestamp
                    }
                }
            )
            
            logger.debug(f"Added messages to conversation {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message to MongoDB: {e}")
            return False
    
    async def list_sessions(self, customer_id: Optional[str] = None, 
                           agent_id: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """List conversation sessions"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            query = {}
            if customer_id:
                query["customer_id"] = customer_id
            if agent_id:
                query["agent_id"] = agent_id
            
            cursor = collection.find(query).sort("updated_at", -1).limit(limit)
            sessions = []
            
            async for doc in cursor:
                if "_id" in doc:
                    del doc["_id"]
                conversation = dict_to_conversation(doc)
                sessions.append({
                    "session_id": conversation.session_id,
                    "customer_id": conversation.customer_id,
                    "agent_id": conversation.agent_id,
                    "persona": conversation.persona,
                    "status": conversation.status,
                    "message_count": len(conversation.messages),
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing conversations from MongoDB: {e}")
            return []
    
    def _convert_history_to_messages(self, history: List[Dict[str, Any]]) -> List[ConversationMessage]:
        """Convert conversation_history format to ConversationMessage format"""
        messages = []
        for item in history:
            # Add user message
            messages.append(ConversationMessage(
                timestamp=item.get("timestamp", datetime.utcnow().isoformat()),
                role="user",
                content=item.get("user_input", "")
            ))
            # Add assistant message
            messages.append(ConversationMessage(
                timestamp=item.get("timestamp", datetime.utcnow().isoformat()),
                role="assistant",
                content=item.get("agent_response", "")
            ))
        return messages
    
    def _convert_messages_to_history(self, messages: List[ConversationMessage]) -> List[Dict[str, Any]]:
        """Convert ConversationMessage format to conversation_history format"""
        history = []
        i = 0
        while i < len(messages):
            if i + 1 < len(messages):
                user_msg = messages[i]
                assistant_msg = messages[i + 1]
                history.append({
                    "timestamp": user_msg.timestamp,
                    "user_input": user_msg.content,
                    "agent_response": assistant_msg.content
                })
                i += 2
            else:
                # Handle odd number of messages
                history.append({
                    "timestamp": messages[i].timestamp,
                    "user_input": messages[i].content if messages[i].role == "user" else "",
                    "agent_response": messages[i].content if messages[i].role == "assistant" else ""
                })
                i += 1
        return history

