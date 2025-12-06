"""
MongoDB Prompt Store
Handles saving and loading prompts for outgoing calls
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

class MongoDBPromptStore:
    """Store and retrieve prompts from MongoDB"""
    
    def __init__(self):
        self.collection_name = "prompts"
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            logger.warning("MongoDB is not available, cannot get collection.")
            return None
        return db[self.collection_name]
    
    async def create_prompt(self, prompt_data: Dict[str, Any], user_id: str) -> Optional[str]:
        """Create a new prompt
        
        Args:
            prompt_data: Dictionary containing:
                - name: Prompt name (required)
                - content: Prompt content/text (required)
                - introduction: Agent introduction/greeting (optional)
                - phoneNumberId: Phone number ID this prompt is linked to (optional)
                - description: Optional description
                - category: Optional category (e.g., "sales", "support", "reminder")
            user_id: User ID for multi-tenancy
        
        Returns:
            Prompt ID if successful, None otherwise
        """
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping prompt creation")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.error("MongoDB collection is None, cannot create prompt")
                return None
            
            # Validate required fields
            if not prompt_data.get("name"):
                raise ValueError("Prompt name is required")
            if not prompt_data.get("content"):
                raise ValueError("Prompt content is required")
            # phoneNumberId is now optional for general prompts
            
            # Add timestamps, metadata, and user ID
            prompt_data["created_at"] = datetime.utcnow().isoformat()
            prompt_data["updated_at"] = datetime.utcnow().isoformat()
            prompt_data["isDeleted"] = False
            prompt_data["userId"] = user_id  # Store user ID for multi-tenancy
            
            # Insert prompt
            result = await collection.insert_one(prompt_data)
            
            logger.info(f"✅ Successfully created prompt '{prompt_data.get('name')}' in MongoDB")
            logger.info(f"   Prompt ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating prompt: {e}", exc_info=True)
            return None
    
    async def get_prompt(self, prompt_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a prompt by ID, optionally filtered by user_id"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping prompt retrieval")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            from bson import ObjectId
            query = {
                "_id": ObjectId(prompt_id),
                "isDeleted": {"$ne": True}
            }
            if user_id:
                query["userId"] = user_id
            prompt = await collection.find_one(query)
            
            if prompt:
                prompt_dict = dict(prompt)
                prompt_dict["id"] = str(prompt_dict["_id"])
                del prompt_dict["_id"]
                return prompt_dict
            return None
            
        except Exception as e:
            logger.error(f"Error getting prompt {prompt_id}: {e}")
            return None
    
    async def list_prompts(self, phone_number_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all prompts, optionally filtered by phone number and user
        
        Args:
            phone_number_id: Optional phone number ID to filter prompts
            user_id: Optional user ID for multi-tenancy filtering
        
        Returns:
            List of prompt dictionaries
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping prompt list")
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.warning("MongoDB collection is None, cannot list prompts")
                return []
            
            # Build query - always exclude deleted prompts
            query = {"isDeleted": {"$ne": True}}
            if phone_number_id:
                query["phoneNumberId"] = phone_number_id
            if user_id:
                query["userId"] = user_id
            
            logger.debug(f"Querying prompts with query: {query}")
            
            prompts = []
            async for doc in collection.find(query).sort("created_at", -1):
                prompt_dict = dict(doc)
                prompt_dict["id"] = str(prompt_dict["_id"])
                del prompt_dict["_id"]
                prompts.append(prompt_dict)
            
            logger.info(f"📝 Found {len(prompts)} prompt(s) in collection '{self.collection_name}'")
            
            return prompts
            
        except Exception as e:
            logger.error(f"❌ Error listing prompts: {e}", exc_info=True)
            return []
    
    async def update_prompt(self, prompt_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a prompt"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping prompt update")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = await collection.update_one(
                {"_id": ObjectId(prompt_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated prompt {prompt_id}")
                return True
            else:
                logger.warning(f"No prompt found with ID {prompt_id} or no changes made")
                return False
                
        except Exception as e:
            logger.error(f"Error updating prompt {prompt_id}: {e}")
            return False
    
    async def delete_prompt(self, prompt_id: str, user_id: Optional[str] = None) -> bool:
        """Soft delete a prompt (set isDeleted=True)
        
        Args:
            prompt_id: Prompt ID to delete
            user_id: Optional user ID for validation (prevents users from deleting other users' prompts)
        """
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping prompt deletion")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            
            # Soft delete: set isDeleted to True
            delete_query = {"_id": ObjectId(prompt_id)}
            if user_id:
                delete_query["userId"] = user_id
            result = await collection.update_one(
                delete_query,
                {"$set": {
                    "isDeleted": True,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Soft deleted prompt {prompt_id} in MongoDB (set isDeleted=True)")
                return True
            else:
                logger.warning(f"No prompt found with ID {prompt_id} or no changes made")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting prompt {prompt_id}: {e}", exc_info=True)
            return False
