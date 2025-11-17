"""
MongoDB Messaging Agent Store
Handles saving and loading messaging agents from MongoDB
Separate collection from call agents for messaging-specific agents
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available
from .mongodb_phone_store import normalize_phone_number

logger = logging.getLogger(__name__)

class MongoDBMessageAgentStore:
    """Store and retrieve messaging agents from MongoDB"""
    
    def __init__(self):
        self.collection_name = "messaging_agents"
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            logger.warning("MongoDB is not available, cannot get collection.")
            return None
        return db[self.collection_name]
    
    async def create_message_agent(self, agent_data: Dict[str, Any]) -> Optional[str]:
        """Create a new messaging agent in MongoDB
        
        Validation rules:
        - If an agent with the same phone number exists, deactivate all existing agents with that number
        - Only one agent per phone number can be active at a time
        - If creating with active=True (or default), ensure no other agents with same phone are active
        """
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping message agent creation")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.error("MongoDB collection is None, cannot create message agent")
                return None
            
            phone_number = agent_data.get("phoneNumber")
            agent_name = agent_data.get("name")
            
            if not phone_number:
                logger.error("Phone number is required for message agent")
                return None
            
            if not agent_name:
                logger.error("Agent name is required for message agent")
                return None
            
            # Normalize phone number to E.164 format
            original_phone = phone_number
            phone_number = normalize_phone_number(phone_number)
            agent_data["phoneNumber"] = phone_number
            if original_phone != phone_number:
                logger.info(f"Normalized message agent phone number: '{original_phone}' -> '{phone_number}'")
            
            # Determine if the new agent will be active
            will_be_active = agent_data.get("active")
            if will_be_active is None:
                will_be_active = True  # Default to active
            
            # If creating an active agent, deactivate all existing agents with the same phone number
            if phone_number and will_be_active:
                existing_agents = []
                async for doc in collection.find({
                    "phoneNumber": phone_number,
                    "isDeleted": {"$ne": True}
                }):
                    existing_agents.append(doc)
                
                if existing_agents:
                    logger.info(f"Found {len(existing_agents)} existing message agent(s) with phone number {phone_number}")
                    
                    deactivate_result = await collection.update_many(
                        {"phoneNumber": phone_number, "isDeleted": {"$ne": True}},
                        {"$set": {"active": False, "updated_at": datetime.utcnow().isoformat()}}
                    )
                    logger.info(f"Deactivated {deactivate_result.modified_count} existing message agent(s) with phone number {phone_number}")
            
            # Add timestamps
            agent_data["created_at"] = datetime.utcnow().isoformat()
            agent_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Ensure new agent is active (unless explicitly set to False)
            if agent_data.get("active") is None:
                agent_data["active"] = True
            
            # Set isDeleted to False by default (soft delete flag)
            agent_data["isDeleted"] = False
            
            # Ensure direction is set to "messaging"
            agent_data["direction"] = "messaging"
            
            # Log the agent data being saved
            logger.info(f"Creating message agent in MongoDB collection '{self.collection_name}': {agent_name} ({phone_number})")
            
            # Insert agent
            result = await collection.insert_one(agent_data)
            
            logger.info(f"✅ Successfully created message agent {result.inserted_id} in MongoDB collection '{self.collection_name}'")
            logger.info(f"   Agent name: {agent_name}")
            logger.info(f"   Phone: {phone_number}")
            logger.info(f"   Active: {agent_data.get('active')}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating message agent in MongoDB: {e}", exc_info=True)
            return None
    
    async def get_message_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a message agent by ID (excluding deleted ones)"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping message agent retrieval")
            return None
        
        if not agent_id:
            logger.warning("Agent ID is required")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            from bson import ObjectId
            from bson.errors import InvalidId
            
            try:
                object_id = ObjectId(agent_id)
            except (InvalidId, ValueError) as e:
                logger.error(f"Invalid agent ID format: {agent_id} - {e}")
                return None
            
            agent = await collection.find_one({
                "_id": object_id,
                "isDeleted": {"$ne": True}
            })
            
            if agent:
                # Convert ObjectId to string and add as 'id'
                agent_dict = dict(agent)
                agent_dict["id"] = str(agent["_id"])
                del agent_dict["_id"]
                return agent_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting message agent: {e}", exc_info=True)
            return None
    
    async def get_message_agent_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get a message agent by phone number (excluding deleted ones)"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping message agent retrieval")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            # Normalize phone number
            normalized_phone = normalize_phone_number(phone_number)
            
            agent = await collection.find_one({
                "phoneNumber": normalized_phone,
                "isDeleted": {"$ne": True}
            })
            
            if agent:
                # Convert ObjectId to string and add as 'id'
                agent_dict = dict(agent)
                agent_dict["id"] = str(agent["_id"])
                del agent_dict["_id"]
                return agent_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting message agent by phone: {e}", exc_info=True)
            return None
    
    async def list_message_agents(self, active_only: bool = False, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """List all message agents
        
        Args:
            active_only: If True, only return agents where active=True
            include_deleted: If True, include soft-deleted agents (isDeleted=True)
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping message agent list")
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Auto-restore agents that are incorrectly marked as deleted
            if not include_deleted:
                deleted_agents_cursor = collection.find({"isDeleted": True})
                restored_count = 0
                async for doc in deleted_agents_cursor:
                    if doc.get("name") and doc.get("phoneNumber"):
                        logger.info(f"🔄 Auto-restoring message agent {doc.get('name')} ({doc.get('phoneNumber')}) - was marked as deleted")
                        await collection.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"isDeleted": False, "updated_at": datetime.utcnow().isoformat()}}
                        )
                        restored_count += 1
                
                if restored_count > 0:
                    logger.info(f"✅ Auto-restored {restored_count} message agent(s) that were incorrectly marked as deleted")
            
            # Build query based on parameters
            query = {}
            
            # Handle deleted agents filter
            if not include_deleted:
                query["isDeleted"] = {"$ne": True}
            
            # Handle active filter
            if active_only:
                query["active"] = True
            
            # Query and convert
            agents = []
            async for doc in collection.find(query).sort("created_at", -1):
                # Convert ObjectId to string
                agent_dict = dict(doc)
                agent_dict["id"] = str(doc["_id"])
                del agent_dict["_id"]
                agents.append(agent_dict)
            
            logger.info(f"Retrieved {len(agents)} message agent(s) from MongoDB")
            return agents
            
        except Exception as e:
            logger.error(f"Error listing message agents: {e}", exc_info=True)
            return []
    
    async def update_message_agent(self, agent_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a message agent"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping message agent update")
            return False
        
        if not agent_id:
            logger.warning("Agent ID is required for update")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            from bson.errors import InvalidId
            
            try:
                object_id = ObjectId(agent_id)
            except (InvalidId, ValueError) as e:
                logger.error(f"Invalid agent ID format: {agent_id} - {e}")
                return False
            
            # Normalize phone number if provided
            if "phoneNumber" in update_data:
                original_phone = update_data["phoneNumber"]
                update_data["phoneNumber"] = normalize_phone_number(original_phone)
                if original_phone != update_data["phoneNumber"]:
                    logger.info(f"Normalized phone number: '{original_phone}' -> '{update_data['phoneNumber']}'")
            
            # Add update timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Ensure direction stays as "messaging"
            update_data["direction"] = "messaging"
            
            result = await collection.update_one(
                {"_id": object_id, "isDeleted": {"$ne": True}},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                logger.warning(f"Message agent {agent_id} not found or is deleted")
                return False
            
            # Return True if document was found (matched_count > 0)
            # modified_count can be 0 if the value was already set to what we're trying to set
            if result.modified_count > 0:
                logger.info(f"✅ Updated message agent {agent_id} (modified {result.modified_count} field(s))")
            else:
                logger.info(f"✅ Message agent {agent_id} already has the requested values (no changes needed)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating message agent: {e}", exc_info=True)
            return False
    
    async def delete_message_agent(self, agent_id: str) -> bool:
        """Soft delete a message agent (set isDeleted=True)"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping message agent deletion")
            return False
        
        if not agent_id:
            logger.warning("Agent ID is required for deletion")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            from bson.errors import InvalidId
            
            try:
                object_id = ObjectId(agent_id)
            except (InvalidId, ValueError) as e:
                logger.error(f"Invalid agent ID format: {agent_id} - {e}")
                return False
            
            result = await collection.update_one(
                {"_id": object_id},
                {"$set": {"isDeleted": True, "active": False, "updated_at": datetime.utcnow().isoformat()}}
            )
            
            if result.matched_count == 0:
                logger.warning(f"Message agent {agent_id} not found")
                return False
            
            logger.info(f"✅ Soft deleted message agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting message agent: {e}", exc_info=True)
            return False

