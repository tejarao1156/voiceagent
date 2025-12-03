"""
MongoDB Phone Number Store
Handles saving and loading registered phone numbers with Twilio credentials
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

def normalize_phone_number(phone_number: str) -> str:
    """
    Normalize phone number to E.164 format (e.g., "+15551234567")

    Args:
        phone_number: Phone number in any format (e.g., "+1 555 123 4567", "555-123-4567", etc.)

    Returns:
        Normalized phone number in E.164 format (e.g., "+15551234567")
    """
    if not phone_number:
        return ""

    # Remove all formatting characters (spaces, dashes, parentheses, dots)
    normalized = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")

    # If it already starts with +, it's already in E.164 format
    if normalized.startswith("+"):
        return normalized

    # If it starts with 1 and is 11 digits (US format without +), add +
    if normalized.startswith("1") and len(normalized) == 11:
        return "+" + normalized

    # For all other cases, add +1 prefix (assuming US numbers by default)
    # This handles 10-digit US numbers and maintains backward compatibility
    # Note: For international numbers, users should provide them in + format
    return "+1" + normalized

class MongoDBPhoneStore:
    """Store and retrieve registered phone numbers from MongoDB"""
    
    def __init__(self):
        self.collection_name = "registered_phone_numbers"
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            logger.warning("MongoDB is not available, cannot get collection.")
            return None
        return db[self.collection_name]
    
    async def register_phone(self, phone_data: Dict[str, Any], user_id: str) -> Optional[str]:
        """Register a new phone number with Twilio credentials
        
        Args:
            phone_data: Dictionary containing:
                - phoneNumber: Phone number (e.g., "+15551234567")
                - twilioAccountSid: Twilio Account SID
                - twilioAuthToken: Twilio Auth Token
                - webhookUrl: Incoming webhook URL (provided by system)
                - statusCallbackUrl: Status callback URL (provided by system)
            user_id: User ID (required for multi-tenancy)
        
        Returns:
            Phone registration ID if successful, None otherwise
        
        Raises:
            ValueError: If phone number already exists and is not deleted
        """
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping phone registration")
            raise ValueError("MongoDB is not available. Please check MongoDB connection.")
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.error("MongoDB collection is None, cannot register phone")
                raise ValueError("MongoDB collection is not available. Please check MongoDB connection.")
            
            phone_number = phone_data.get("phoneNumber")
            if not phone_number:
                logger.error("Phone number is required for registration")
                raise ValueError("Phone number is required for registration")
            
            # Normalize phone number to E.164 format
            normalized_phone = normalize_phone_number(phone_number)
            logger.info(f"Normalizing phone number: '{phone_number}' -> '{normalized_phone}'")
            
            # Get the type from phone_data (default to 'calls' for backward compatibility)
            registration_type = phone_data.get("type", "calls")
            
            # Check if phone number already exists FOR THIS SPECIFIC TYPE AND USER
            # This allows the same phone number to be registered for both 'calls' and 'messages' separately
            # But each user can only register a phone number once per type
            # Exclude deleted phones from the check
            try:
                existing = await collection.find_one({
                    "phoneNumber": normalized_phone,
                    "type": registration_type,  # Check within the same type only
                    "userId": user_id,  # Check within the same user
                    "isDeleted": {"$ne": True}
                })
                if not existing:
                    # Also check if any phone with different format exists (normalize all and compare)
                    # Exclude deleted phones and check within same type and user
                    async for doc in collection.find({
                        "type": registration_type,
                        "userId": user_id,
                        "isDeleted": {"$ne": True}
                    }):
                        stored_phone = doc.get("phoneNumber", "")
                        if normalize_phone_number(stored_phone) == normalized_phone:
                            existing = doc
                            break
            except Exception as e:
                logger.error(f"Error checking for existing phone: {e}", exc_info=True)
                raise ValueError(f"Error checking if phone number exists: {str(e)}")
            
            if existing:
                existing_phone_id = str(existing.get("_id"))
                existing_is_deleted = existing.get("isDeleted", False)
                existing_is_active = existing.get("isActive", True)
                existing_type = existing.get("type", "calls")
                
                # If phone exists for this type and is not deleted, raise error (duplicate validation)
                if not existing_is_deleted:
                    error_msg = f"Phone number {normalized_phone} is already registered for type '{registration_type}'. Please delete the existing registration first or use a different phone number."
                    logger.warning(f"❌ Duplicate phone number detected: {normalized_phone} (original: {phone_number}) already registered for type '{registration_type}' (ID: {existing_phone_id}, Active: {existing_is_active})")
                    raise ValueError(error_msg)
                
                # If phone exists but is deleted, allow re-registration (restore it)
                logger.info(f"Phone number {normalized_phone} for type '{registration_type}' was previously deleted. Restoring registration...")
                # Update the existing record instead of creating new one
                # Only update the fields we want to change, preserve existing _id
                update_data = {
                    "phoneNumber": normalized_phone,
                    "originalPhoneNumber": phone_number,
                    "provider": phone_data.get("provider", "twilio"),  # Store provider
                    "twilioAccountSid": phone_data.get("twilioAccountSid"),
                    "twilioAuthToken": phone_data.get("twilioAuthToken"),
                    "twilioAccountName": phone_data.get("twilioAccountName", "Twilio 0"),
                    "webhookUrl": phone_data.get("webhookUrl"),
                    "statusCallbackUrl": phone_data.get("statusCallbackUrl"),
                    "smsWebhookUrl": phone_data.get("smsWebhookUrl"),  # Add SMS webhook support
                    "userId": user_id,  # Store user ID
                    "type": registration_type,  # Ensure type is set
                    "isDeleted": False,
                    "isActive": True,
                    "updated_at": datetime.utcnow().isoformat()
                }
                await collection.update_one(
                    {"_id": existing.get("_id")},
                    {"$set": update_data}
                )
                logger.info(f"✅ Restored previously deleted phone number {normalized_phone} for type '{registration_type}' (ID: {existing_phone_id})")
                return existing_phone_id
            
            # Store normalized phone number
            phone_data["phoneNumber"] = normalized_phone
            phone_data["originalPhoneNumber"] = phone_number  # Keep original for reference
            
            # Add timestamps and user ID
            phone_data["created_at"] = datetime.utcnow().isoformat()
            phone_data["updated_at"] = datetime.utcnow().isoformat()
            phone_data["isActive"] = True
            phone_data["userId"] = user_id  # Store user ID for multi-tenancy
            
            # NEW: Add isDeleted, uuid, and type
            phone_data["isDeleted"] = False
            import uuid
            phone_data["uuid"] = str(uuid.uuid4())
            
            # Set type (default to 'calls' if not provided for backward compatibility)
            if "type" not in phone_data:
                phone_data["type"] = "calls"
            
            # Insert phone registration
            result = await collection.insert_one(phone_data)
            
            logger.info(f"✅ Successfully registered phone number {normalized_phone} (original: {phone_number}) in MongoDB")
            logger.info(f"   Phone ID: {result.inserted_id}")
            logger.info(f"   Type: {phone_data.get('type')}")
            return str(result.inserted_id)
            
        except ValueError:
            # Re-raise ValueError (duplicate phone, validation errors) to be handled by API endpoint
            raise
        except Exception as e:
            # Catch other unexpected errors (MongoDB connection issues, etc.)
            logger.error(f"❌ Unexpected error registering phone number: {e}", exc_info=True)
            raise ValueError(f"Failed to register phone number due to an unexpected error: {str(e)}")
    
    async def get_phone(self, phone_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a registered phone by ID, optionally filtered by user_id"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping phone retrieval")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            from bson import ObjectId
            query = {"_id": ObjectId(phone_id)}
            if user_id:
                query["userId"] = user_id  # Filter by user if provided
            phone = await collection.find_one(query)
            
            if phone:
                phone_dict = dict(phone)
                phone_dict["id"] = str(phone_dict["_id"])
                del phone_dict["_id"]
                return phone_dict
            return None
            
        except Exception as e:
            logger.error(f"Error getting phone {phone_id}: {e}")
            return None
    
    async def get_phone_by_number(self, phone_number: str, type_filter: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a registered phone by phone number (with normalization and optional type filtering)
        
        Args:
            phone_number: Phone number to lookup
            type_filter: Optional filter for 'calls' or 'messages' type
            user_id: Optional user ID filter for multi-tenancy
        
        Returns:
            Phone dict if found, None otherwise
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping phone retrieval")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            # Normalize the input phone number
            normalized_phone = normalize_phone_number(phone_number)
            log_suffix = f" (type={type_filter})" if type_filter else ""
            logger.debug(f"Looking up phone number: '{phone_number}' -> normalized: '{normalized_phone}'{log_suffix}")
            
            # Build query - exclude deleted phones
            query = {
                "phoneNumber": normalized_phone,
                "isDeleted": {"$ne": True}
            }
            
            # Add type filter if provided
            if type_filter:
                query["type"] = type_filter
            
            # Add user filter if provided
            if user_id:
                query["userId"] = user_id
            
            # First try exact match with normalized number
            phone = await collection.find_one(query)
            
            if phone:
                phone_dict = dict(phone)
                phone_dict["id"] = str(phone_dict["_id"])
                del phone_dict["_id"]
                logger.debug(f"✅ Found phone by normalized number: {normalized_phone}{log_suffix}")
                return phone_dict
            
            # If not found, try to find by normalizing all stored phones
            # This handles cases where phone was stored in a different format
            search_query = {"isDeleted": {"$ne": True}}
            if type_filter:
                search_query["type"] = type_filter
            if user_id:
                search_query["userId"] = user_id
            
            async for doc in collection.find(search_query):
                stored_phone = doc.get("phoneNumber", "")
                if normalize_phone_number(stored_phone) == normalized_phone:
                    phone_dict = dict(doc)
                    phone_dict["id"] = str(phone_dict["_id"])
                    del phone_dict["_id"]
                    logger.info(f"✅ Found phone by normalized comparison: stored '{stored_phone}' matches '{normalized_phone}'{log_suffix}")
                    return phone_dict
            
            logger.warning(f"❌ Phone number not found: '{phone_number}' (normalized: '{normalized_phone}'){log_suffix}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting phone by number {phone_number}: {e}")
            return None
    
    async def list_phones(self, active_only: bool = True, type_filter: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered phone numbers
        
        Args:
            active_only: If True, only return active phones
            type_filter: Optional filter for 'calls' or 'messages'
            user_id: Optional user ID filter for multi-tenancy
        
        Returns:
            List of phone dictionaries
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping phone list")
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.warning("MongoDB collection is None, cannot list phones")
                return []
            
            # Build query - always exclude deleted phones
            query = {"isDeleted": {"$ne": True}}  # Exclude soft-deleted phones
            
            if active_only:
                query["isActive"] = True
            
            # Add type filter if provided
            if type_filter:
                query["type"] = type_filter
            
            # Add user filter if provided
            if user_id:
                query["userId"] = user_id
            
            logger.debug(f"Querying phones with query: {query}, active_only={active_only}, type={type_filter}, user_id={user_id}")
            
            phones = []
            total_count = 0
            async for doc in collection.find(query).sort("created_at", -1):
                total_count += 1
                phone_dict = dict(doc)
                phone_dict["id"] = str(phone_dict["_id"])
                del phone_dict["_id"]
                # Don't expose sensitive auth token in list
                if "twilioAuthToken" in phone_dict:
                    phone_dict["twilioAuthToken"] = "***hidden***"
                phones.append(phone_dict)
            
            logger.info(f"📞 Found {len(phones)} phone(s) in collection '{self.collection_name}' (total scanned: {total_count})")
            if phones:
                for phone in phones:
                    logger.debug(f"   - {phone.get('phoneNumber', 'N/A')} (isActive: {phone.get('isActive', 'not set')}, type: {phone.get('type', 'N/A')})")
            
            return phones
            
        except Exception as e:
            logger.error(f"❌ Error listing phones: {e}", exc_info=True)
            return []
    
    async def update_phone(self, phone_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a registered phone number"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping phone update")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = await collection.update_one(
                {"_id": ObjectId(phone_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated phone {phone_id}")
                return True
            else:
                logger.warning(f"No phone found with ID {phone_id} or no changes made")
                return False
                
        except Exception as e:
            logger.error(f"Error updating phone {phone_id}: {e}")
            return False
    
    async def delete_phone(self, phone_id: str, user_id: Optional[str] = None) -> bool:
        """Soft delete a registered phone number (set isDeleted=True) and deactivate associated agents"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping phone deletion")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            
            # First, get the phone number before deleting (to deactivate associated agents)
            query = {"_id": ObjectId(phone_id)}
            if user_id:
                query["userId"] = user_id  # Only allow deletion if user owns the phone
            phone_doc = await collection.find_one(query)
            if not phone_doc:
                logger.warning(f"No phone found with ID {phone_id}")
                return False
            
            phone_number = phone_doc.get("phoneNumber")
            normalized_phone = normalize_phone_number(phone_number) if phone_number else None
            
            # Soft delete: set isDeleted to True instead of actually deleting
            result = await collection.update_one(
                {"_id": ObjectId(phone_id)},
                {"$set": {
                    "isDeleted": True,
                    "isActive": False,  # Also deactivate when deleting
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Soft deleted phone {phone_id} in MongoDB (set isDeleted=True)")
                
                # Deactivate all agents associated with this phone number
                if normalized_phone:
                    try:
                        from databases.mongodb_agent_store import MongoDBAgentStore
                        agent_store = MongoDBAgentStore()
                        deactivated_count = await agent_store.deactivate_agents_by_phone(normalized_phone)
                        if deactivated_count > 0:
                            logger.info(f"✅ Deactivated {deactivated_count} agent(s) associated with phone number {normalized_phone}")
                        else:
                            logger.debug(f"No active agents found for phone number {normalized_phone}")
                    except Exception as e:
                        logger.error(f"Error deactivating agents for phone {normalized_phone}: {e}", exc_info=True)
                        # Don't fail phone deletion if agent deactivation fails
                
                return True
            else:
                logger.warning(f"No phone found with ID {phone_id} or no changes made")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting phone {phone_id}: {e}", exc_info=True)
            return False

