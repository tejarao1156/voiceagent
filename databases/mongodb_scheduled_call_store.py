"""
MongoDB Scheduled Calls Store
Handles saving and loading scheduled outgoing calls
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

class MongoDBScheduledCallStore:
    """Store and retrieve scheduled calls from MongoDB"""
    
    def __init__(self):
        self.collection_name = "scheduled_calls"
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            logger.warning("MongoDB is not available, cannot get collection.")
            return None
        return db[self.collection_name]
    
    async def create_scheduled_call(self, call_data: Dict[str, Any]) -> Optional[str]:
        """Create a new scheduled call
        
        Args:
            call_data: Dictionary containing:
                - callType: "ai" or "normal" (required)
                - fromPhoneNumberId: Phone number ID to call from (required)
                - toPhoneNumbers: List of phone numbers to call (required)
                - scheduledDateTime: ISO datetime string (required)
                - promptId: Prompt ID for AI calls (optional, required for AI calls)
                - promptContent: Prompt content (optional, for quick reference)
                - status: "pending", "in_progress", "completed", "failed", "cancelled"
        
        Returns:
            Scheduled call ID if successful, None otherwise
        """
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping scheduled call creation")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.error("MongoDB collection is None, cannot create scheduled call")
                return None
            
            # Validate required fields
            if not call_data.get("callType"):
                raise ValueError("Call type is required (ai or normal)")
            if call_data.get("callType") not in ["ai", "normal"]:
                raise ValueError("Call type must be 'ai' or 'normal'")
            if not call_data.get("fromPhoneNumberId"):
                raise ValueError("From phone number ID is required")
            if not call_data.get("toPhoneNumbers") or not isinstance(call_data.get("toPhoneNumbers"), list):
                raise ValueError("To phone numbers list is required")
            if not call_data.get("scheduledDateTime"):
                raise ValueError("Scheduled date/time is required")
            
            # For AI calls, prompt is required
            if call_data.get("callType") == "ai" and not call_data.get("promptId"):
                raise ValueError("Prompt ID is required for AI calls")
            
            # Add timestamps and metadata
            call_data["created_at"] = datetime.utcnow().isoformat()
            call_data["updated_at"] = datetime.utcnow().isoformat()
            call_data["status"] = call_data.get("status", "scheduled")
            call_data["isDeleted"] = False
            
            # Insert scheduled call
            result = await collection.insert_one(call_data)
            
            logger.info(f"✅ Successfully created scheduled call in MongoDB")
            logger.info(f"   Call ID: {result.inserted_id}")
            logger.info(f"   Type: {call_data.get('callType')}")
            logger.info(f"   To: {len(call_data.get('toPhoneNumbers', []))} number(s)")
            logger.info(f"   Scheduled: {call_data.get('scheduledDateTime')}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating scheduled call: {e}", exc_info=True)
            return None
    
    async def get_scheduled_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get a scheduled call by ID"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping scheduled call retrieval")
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            from bson import ObjectId
            call = await collection.find_one({
                "_id": ObjectId(call_id),
                "isDeleted": {"$ne": True}
            })
            
            if call:
                call_dict = dict(call)
                call_dict["id"] = str(call_dict["_id"])
                del call_dict["_id"]
                return call_dict
            return None
            
        except Exception as e:
            logger.error(f"Error getting scheduled call {call_id}: {e}")
            return None
    
    async def list_scheduled_calls(
        self, 
        phone_number_id: Optional[str] = None,
        status: Optional[str] = None,
        call_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List scheduled calls with optional filters
        
        Args:
            phone_number_id: Optional phone number ID to filter calls
            status: Optional status filter (scheduled, in_progress, completed, failed, cancelled)
            call_type: Optional call type filter (ai, normal)
        
        Returns:
            List of scheduled call dictionaries
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping scheduled calls list")
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.warning("MongoDB collection is None, cannot list scheduled calls")
                return []
            
            # Build query - always exclude deleted calls
            query = {"isDeleted": {"$ne": True}}
            if phone_number_id:
                query["fromPhoneNumberId"] = phone_number_id
            if status:
                query["status"] = status
            if call_type:
                query["callType"] = call_type
            
            logger.debug(f"Querying scheduled calls with query: {query}")
            
            calls = []
            async for doc in collection.find(query).sort("scheduledDateTime", 1):
                call_dict = dict(doc)
                call_dict["id"] = str(call_dict["_id"])
                del call_dict["_id"]
                calls.append(call_dict)
            
            logger.info(f"📞 Found {len(calls)} scheduled call(s) in collection '{self.collection_name}'")
            
            return calls
            
        except Exception as e:
            logger.error(f"❌ Error listing scheduled calls: {e}", exc_info=True)
            return []
    
    async def update_scheduled_call(self, call_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a scheduled call"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping scheduled call update")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = await collection.update_one(
                {"_id": ObjectId(call_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated scheduled call {call_id}")
                return True
            else:
                logger.warning(f"No scheduled call found with ID {call_id} or no changes made")
                return False
                
        except Exception as e:
            logger.error(f"Error updating scheduled call {call_id}: {e}")
            return False
    
    async def delete_scheduled_call(self, call_id: str) -> bool:
        """Soft delete a scheduled call (set isDeleted=True)"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping scheduled call deletion")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            from bson import ObjectId
            
            # Soft delete: set isDeleted to True
            result = await collection.update_one(
                {"_id": ObjectId(call_id)},
                {"$set": {
                    "isDeleted": True,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Soft deleted scheduled call {call_id} in MongoDB (set isDeleted=True)")
                return True
            else:
                logger.warning(f"No scheduled call found with ID {call_id} or no changes made")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting scheduled call {call_id}: {e}", exc_info=True)
            return False
    
    async def get_pending_calls(self, before_datetime: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending calls that should be executed
        
        Args:
            before_datetime: Optional ISO datetime string - get calls scheduled before this time
        
        Returns:
            List of pending scheduled call dictionaries
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping pending calls retrieval")
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            query = {
                "isDeleted": {"$ne": True},
                "status": "scheduled"  # Changed from 'pending' to 'scheduled'
            }
            
            if before_datetime:
                query["scheduledDateTime"] = {"$lte": before_datetime}
            
            calls = []
            async for doc in collection.find(query).sort("scheduledDateTime", 1):
                call_dict = dict(doc)
                call_dict["id"] = str(call_dict["_id"])
                del call_dict["_id"]
                calls.append(call_dict)
            
            return calls
            
        except Exception as e:
            logger.error(f"Error getting pending calls: {e}", exc_info=True)
            return []
