"""
MongoDB Voice Agent Store
Handles saving and loading voice agents from MongoDB
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available
from .mongodb_phone_store import normalize_phone_number

logger = logging.getLogger(__name__)

class MongoDBAgentStore:
    """Store and retrieve voice agents from MongoDB"""
    
    def __init__(self):
        self.collection_name = "voice_agents"
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            logger.warning("MongoDB is not available, cannot get collection.")
            return None
        return db[self.collection_name]
    
    async def create_agent(self, agent_data: Dict[str, Any]) -> Optional[str]:
        """Create a new agent in MongoDB
        
        Validation rules:
        - If an agent with the same phone number exists, deactivate all existing agents with that number
        - Only one agent per phone number can be active at a time
        - If creating with active=True (or default), ensure no other agents with same phone are active
        """
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping agent creation")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.error("MongoDB collection is None, cannot create agent")
                return None
            
            phone_number = agent_data.get("phoneNumber")
            agent_name = agent_data.get("name")
            
            # Normalize phone number to E.164 format
            if phone_number:
                original_phone = phone_number
                phone_number = normalize_phone_number(phone_number)
                agent_data["phoneNumber"] = phone_number
                if original_phone != phone_number:
                    logger.info(f"Normalized agent phone number: '{original_phone}' -> '{phone_number}'")
            
            # Determine if the new agent will be active
            will_be_active = agent_data.get("active")
            if will_be_active is None:
                will_be_active = True  # Default to active
            
            # If creating an active agent, deactivate all existing agents with the same phone number
            # Check both exact match and normalized match
            if phone_number and will_be_active:
                existing_agents = []
                # First try exact match
                async for doc in collection.find({
                    "phoneNumber": phone_number,
                    "isDeleted": {"$ne": True}
                }):
                    existing_agents.append(doc)
                
                # Also check normalized matches (for backward compatibility with old formats)
                if not existing_agents:
                    async for doc in collection.find({"isDeleted": {"$ne": True}}):
                        stored_phone = doc.get("phoneNumber", "")
                        if normalize_phone_number(stored_phone) == phone_number:
                            existing_agents.append(doc)
                
                if existing_agents:
                    logger.info(f"Found {len(existing_agents)} existing agent(s) with phone number {phone_number}")
                    
                    # Check if any existing agent has the same name (potential duplicate)
                    same_name_agents = [a for a in existing_agents if a.get("name") == agent_name]
                    
                    if same_name_agents:
                        logger.warning(f"Agent with same name '{agent_name}' and phone '{phone_number}' already exists")
                        # User might be trying to create a duplicate - we'll still create it but deactivate old ones
                    
                    # Deactivate all existing agents with this phone number (normalized match)
                    # Get all phone numbers that normalize to the same value
                    phone_numbers_to_deactivate = [phone_number]
                    async for doc in collection.find({"isDeleted": {"$ne": True}}):
                        stored_phone = doc.get("phoneNumber", "")
                        if stored_phone not in phone_numbers_to_deactivate and normalize_phone_number(stored_phone) == phone_number:
                            phone_numbers_to_deactivate.append(stored_phone)
                    
                    deactivate_result = await collection.update_many(
                        {"phoneNumber": {"$in": phone_numbers_to_deactivate}, "isDeleted": {"$ne": True}},
                        {"$set": {"active": False, "updated_at": datetime.utcnow().isoformat()}}
                    )
                    logger.info(f"Deactivated {deactivate_result.modified_count} existing agent(s) with phone number {phone_number} to ensure only one active agent per number")
            
            # Add timestamps
            agent_data["created_at"] = datetime.utcnow().isoformat()
            agent_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Ensure new agent is active (unless explicitly set to False)
            if agent_data.get("active") is None:
                agent_data["active"] = True
            
            # Set isDeleted to False by default (soft delete flag)
            agent_data["isDeleted"] = False
            
            # Log the agent data being saved (without sensitive info)
            logger.info(f"Creating agent in MongoDB collection '{self.collection_name}': {agent_name} ({phone_number})")
            
            # Insert agent
            result = await collection.insert_one(agent_data)
            
            logger.info(f"✅ Successfully created agent {result.inserted_id} in MongoDB collection '{self.collection_name}'")
            logger.info(f"   Agent name: {agent_name}")
            logger.info(f"   Phone: {phone_number}")
            logger.info(f"   Active: {agent_data.get('active')}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating agent in MongoDB: {e}", exc_info=True)
            return None
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get an agent by ID (excluding deleted ones)"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping agent retrieval")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            from bson import ObjectId
            agent = await collection.find_one({
                "_id": ObjectId(agent_id),
                "isDeleted": {"$ne": True}
            })
            
            if agent:
                # Convert ObjectId to string and add as 'id'
                agent_dict = dict(agent)
                agent_dict["id"] = str(agent_dict["_id"])
                del agent_dict["_id"]
                return agent_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent from MongoDB: {e}")
            return None
    
    async def get_agent_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get an agent by phone number (with normalization)"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping agent retrieval")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            # Normalize the input phone number
            normalized_phone = normalize_phone_number(phone_number)
            logger.debug(f"Looking up agent by phone: '{phone_number}' -> normalized: '{normalized_phone}'")
            
            # First try exact match with normalized number
            agent = await collection.find_one({
                "phoneNumber": normalized_phone,
                "isDeleted": {"$ne": True}
            })
            
            if agent:
                agent_dict = dict(agent)
                agent_dict["id"] = str(agent_dict["_id"])
                del agent_dict["_id"]
                logger.debug(f"✅ Found agent by normalized phone: {normalized_phone}")
                return agent_dict
            
            # If not found, try to find by normalizing all stored agents
            async for doc in collection.find({"isDeleted": {"$ne": True}}):
                stored_phone = doc.get("phoneNumber", "")
                if normalize_phone_number(stored_phone) == normalized_phone:
                    agent_dict = dict(doc)
                    agent_dict["id"] = str(agent_dict["_id"])
                    del agent_dict["_id"]
                    logger.info(f"✅ Found agent by normalized comparison: stored '{stored_phone}' matches '{normalized_phone}'")
                    return agent_dict
            
            logger.warning(f"❌ No agent found for phone: '{phone_number}' (normalized: '{normalized_phone}')")
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent by phone from MongoDB: {e}")
            return None
    
    async def list_agents(self, active_only: bool = False, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """List all agents
        
        Args:
            active_only: If True, only return agents where active=True
            include_deleted: If True, include soft-deleted agents (isDeleted=True)
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping agent list")
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Auto-restore agents that are incorrectly marked as deleted
            # Check ALL agents in MongoDB first (before filtering) to restore any that shouldn't be deleted
            deleted_agents_cursor = collection.find({"isDeleted": True})
            restored_count = 0
            async for doc in deleted_agents_cursor:
                # Auto-restore agents that have valid data but are marked as deleted
                if doc.get("name") and doc.get("phoneNumber"):
                    logger.info(f"🔄 Auto-restoring agent {doc.get('name')} ({doc.get('phoneNumber')}) - was marked as deleted")
                    await collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"isDeleted": False, "updated_at": datetime.utcnow().isoformat()}}
                    )
                    restored_count += 1
            
            if restored_count > 0:
                logger.info(f"✅ Auto-restored {restored_count} agent(s) that were incorrectly marked as deleted")
            
            # Build query based on parameters (after restoration)
            query = {}
            
            # Handle deleted agents filter
            if not include_deleted:
                # Exclude deleted agents: isDeleted is not True (handles missing field, False, null, etc.)
                query["isDeleted"] = {"$ne": True}
            
            # Handle active filter
            if active_only:
                # For active_only, also require active field to be True
                query["active"] = True
            
            cursor = collection.find(query).sort("created_at", -1)
            agents = []
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                
                # Normalize field names: convert snake_case to camelCase for API consistency
                # Handle phone_number -> phoneNumber
                if "phone_number" in doc and "phoneNumber" not in doc:
                    doc["phoneNumber"] = doc.pop("phone_number")
                # Handle is_active -> active (if needed)
                if "is_active" in doc and "active" not in doc:
                    doc["active"] = doc.pop("is_active")
                elif "is_active" in doc and "active" in doc:
                    # Keep active, remove is_active
                    del doc["is_active"]
                
                # Ensure active field exists and is boolean (default to True if missing)
                if "active" not in doc:
                    doc["active"] = True  # Default to active if field is missing
                elif doc.get("active") is None:
                    doc["active"] = True  # Default to active if None
                
                # Check if the agent's phone number is deleted
                phone_number = doc.get("phoneNumber")
                phone_is_deleted = False
                if phone_number:
                    try:
                        from .mongodb_phone_store import MongoDBPhoneStore
                        phone_store = MongoDBPhoneStore()
                        phone = await phone_store.get_phone_by_number(phone_number)
                        # If phone is not found or is deleted, mark as deleted
                        if not phone or phone.get("isDeleted", False):
                            phone_is_deleted = True
                    except Exception as e:
                        logger.debug(f"Error checking phone status for {phone_number}: {e}")
                        # If we can't check, assume not deleted (don't block agent)
                
                doc["phoneIsDeleted"] = phone_is_deleted
                
                agents.append(doc)
            
            return agents
            
        except Exception as e:
            logger.error(f"Error listing agents from MongoDB: {e}")
            return []
    
    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """Update an agent (phone number cannot be updated)
        
        Validation rules:
        - If setting active=True, deactivate all other agents with the same phone number
        - Only one agent per phone number can be active at a time
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping agent update")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            # Remove phoneNumber from updates - phone numbers cannot be edited
            if "phoneNumber" in updates:
                logger.warning(f"Attempted to update phone number for agent {agent_id} - phone numbers cannot be edited")
                del updates["phoneNumber"]
            
            # Prevent isDeleted from being updated via this method (use delete_agent instead)
            if "isDeleted" in updates:
                logger.warning(f"Attempted to update isDeleted for agent {agent_id} - use delete_agent method instead")
                del updates["isDeleted"]
            
            # If activating an agent, deactivate all other agents with the same phone number
            if updates.get("active") is True:
                from bson import ObjectId
                # Get the current agent to find its phone number
                current_agent = await collection.find_one({
                    "_id": ObjectId(agent_id),
                    "isDeleted": {"$ne": True}
                })
                
                if current_agent:
                    phone_number = current_agent.get("phoneNumber")
                    if phone_number:
                        # Deactivate all other agents with the same phone number (excluding this one)
                        deactivate_result = await collection.update_many(
                            {
                                "phoneNumber": phone_number,
                                "_id": {"$ne": ObjectId(agent_id)},
                                "isDeleted": {"$ne": True}
                            },
                            {"$set": {"active": False, "updated_at": datetime.utcnow().isoformat()}}
                        )
                        if deactivate_result.modified_count > 0:
                            logger.info(f"Deactivated {deactivate_result.modified_count} other agent(s) with phone number {phone_number} to ensure only one active agent per number")
                else:
                    logger.warning(f"Agent {agent_id} not found, cannot update")
                    return False
            
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            from bson import ObjectId
            result = await collection.update_one(
                {"_id": ObjectId(agent_id), "isDeleted": {"$ne": True}},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated agent {agent_id} in MongoDB")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating agent in MongoDB: {e}")
            return False
    
    async def deactivate_agents_by_phone(self, phone_number: str, exclude_agent_id: Optional[str] = None) -> int:
        """Deactivate all agents with a given phone number, optionally excluding one agent
        
        Args:
            phone_number: Phone number to search for (should be normalized)
            exclude_agent_id: Optional agent ID to exclude from deactivation
            
        Returns:
            Number of agents deactivated
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping deactivation")
            return 0
        
        try:
            collection = self._get_collection()
            if collection is None:
                return 0
            
            from bson import ObjectId
            
            # Normalize phone number for consistent matching
            normalized_phone = normalize_phone_number(phone_number)
            logger.debug(f"Deactivating agents for phone: '{phone_number}' -> normalized: '{normalized_phone}'")
            
            # Build query (exclude deleted agents)
            # Try exact match first
            query = {"phoneNumber": normalized_phone, "isDeleted": {"$ne": True}}
            if exclude_agent_id:
                query["_id"] = {"$ne": ObjectId(exclude_agent_id)}
            
            # Deactivate matching agents
            result = await collection.update_many(
                query,
                {"$set": {"active": False, "updated_at": datetime.utcnow().isoformat()}}
            )
            
            # Also check for agents with different phone formats that normalize to the same value
            if result.modified_count == 0:
                # Find all non-deleted agents and check if their phone normalizes to the same value
                async for doc in collection.find({"isDeleted": {"$ne": True}}):
                    stored_phone = doc.get("phoneNumber", "")
                    if normalize_phone_number(stored_phone) == normalized_phone:
                        agent_id = str(doc.get("_id"))
                        if exclude_agent_id and agent_id == exclude_agent_id:
                            continue
                        await collection.update_one(
                            {"_id": doc.get("_id")},
                            {"$set": {"active": False, "updated_at": datetime.utcnow().isoformat()}}
                        )
                        result.modified_count += 1
            
            if result.modified_count > 0:
                logger.info(f"✅ Deactivated {result.modified_count} agent(s) with phone number {normalized_phone}")
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error deactivating agents by phone in MongoDB: {e}", exc_info=True)
            return 0
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Soft delete an agent by setting isDeleted to True"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping agent deletion")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            # Soft delete: set isDeleted to True instead of actually deleting
            result = await collection.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": {
                    "isDeleted": True,
                    "active": False,  # Also deactivate when deleting
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"Soft deleted agent {agent_id} in MongoDB (set isDeleted=True)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting agent from MongoDB: {e}")
            return False

