"""
MongoDB Contact List Store
Simplified: Single collection stores both metadata and phones
No versioning - just add/delete contacts
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from bson import ObjectId
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)


class MongoDBContactListStore:
    """Store and retrieve contact lists from MongoDB
    
    Uses single 'campaign_contacts' collection with schema:
    {
        _id: ObjectId,
        name: str,
        description: str,
        userId: str,
        phones: [str],  # All phone numbers in one array
        contact_count: int,
        created_at: str,
        updated_at: str,
        isDeleted: bool
    }
    """
    
    def __init__(self):
        self.collection_name = "campaign_contacts"
    
    def _get_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.collection_name]
    
    # ==================== CONTACT LIST METHODS ====================
    
    async def create_list(self, name: str, user_id: str, description: str = "") -> Optional[str]:
        """Create a new empty contact list"""
        if not is_mongodb_available():
            return None
        
        try:
            coll = self._get_collection()
            if coll is None:
                return None
            
            doc = {
                "name": name,
                "description": description,
                "userId": user_id,
                "phones": [],  # Empty array for new list
                "contact_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "isDeleted": False
            }
            
            result = await coll.insert_one(doc)
            list_id = str(result.inserted_id)
            
            logger.info(f"✅ Created contact list {list_id}: {name}")
            return list_id
            
        except Exception as e:
            logger.error(f"Error creating contact list: {e}", exc_info=True)
            return None
    
    async def get_list(self, list_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a contact list by ID"""
        if not is_mongodb_available():
            return None
        
        try:
            coll = self._get_collection()
            if coll is None:
                return None
            
            query = {"_id": ObjectId(list_id), "isDeleted": {"$ne": True}}
            if user_id:
                query["userId"] = user_id
            
            doc = await coll.find_one(query)
            if doc:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                # Update contact_count from phones array length
                doc["contact_count"] = len(doc.get("phones", []))
                return doc
            return None
            
        except Exception as e:
            logger.error(f"Error getting contact list: {e}")
            return None
    
    async def list_lists(self, user_id: str) -> List[Dict[str, Any]]:
        """List all contact lists for a user"""
        if not is_mongodb_available():
            return []
        
        try:
            coll = self._get_collection()
            if coll is None:
                return []
            
            result = []
            # Only return metadata, not the full phones array
            async for doc in coll.find(
                {"userId": user_id, "isDeleted": {"$ne": True}},
                {"phones": 0}  # Exclude phones array for listing
            ).sort("updated_at", -1):
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing contact lists: {e}")
            return []
    
    async def update_list(self, list_id: str, update_data: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """Update contact list metadata"""
        if not is_mongodb_available():
            return False
        
        try:
            coll = self._get_collection()
            if coll is None:
                return False
            
            query = {"_id": ObjectId(list_id)}
            if user_id:
                query["userId"] = user_id
            
            # Don't allow updating phones through this method
            update_data.pop("phones", None)
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = await coll.update_one(query, {"$set": update_data})
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating contact list: {e}")
            return False
    
    async def delete_list(self, list_id: str, user_id: Optional[str] = None) -> bool:
        """Soft delete a contact list"""
        if not is_mongodb_available():
            return False
        
        try:
            coll = self._get_collection()
            if coll is None:
                return False
            
            query = {"_id": ObjectId(list_id)}
            if user_id:
                query["userId"] = user_id
            
            result = await coll.update_one(
                query,
                {"$set": {"isDeleted": True, "updated_at": datetime.utcnow().isoformat()}}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting contact list: {e}")
            return False
    
    # ==================== CONTACTS METHODS ====================
    
    async def add_contacts(
        self, 
        list_id: str, 
        contacts: List[Dict[str, Any]],
        filename: str = "upload.xlsx",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add contacts to a list - pushes to phones array
        
        Args:
            list_id: Contact list ID
            contacts: List of contact dicts with 'original', 'normalized', 'status'
            filename: Original filename (for logging only)
            user_id: User who uploaded (unused, for API compat)
            
        Returns:
            {"added": count, "duplicates": count, "invalid": count}
        """
        if not is_mongodb_available():
            return {"added": 0, "duplicates": 0, "invalid": 0}
        
        try:
            coll = self._get_collection()
            if coll is None:
                return {"added": 0, "duplicates": 0, "invalid": 0}
            
            # Get existing phones from this list
            contact_list = await self.get_list(list_id)
            if not contact_list:
                logger.error(f"Contact list {list_id} not found")
                return {"added": 0, "duplicates": 0, "invalid": 0}
            
            existing_set = set(contact_list.get("phones", []))
            
            stats = {"added": 0, "duplicates": 0, "invalid": 0}
            phones_to_add = []
            
            for contact in contacts:
                normalized = contact.get("normalized")
                status = contact.get("status", "active")
                
                if status == "invalid" or not normalized:
                    stats["invalid"] += 1
                    continue
                
                if normalized in existing_set:
                    stats["duplicates"] += 1
                    continue
                
                # Add to set to catch duplicates within this upload
                existing_set.add(normalized)
                phones_to_add.append(normalized)
            
            if phones_to_add:
                # Push new phones to array and update count
                await coll.update_one(
                    {"_id": ObjectId(list_id)},
                    {
                        "$push": {"phones": {"$each": phones_to_add}},
                        "$set": {
                            "contact_count": len(existing_set),
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    }
                )
            
            stats["added"] = len(phones_to_add)
            
            logger.info(f"✅ Added {stats['added']} phones to list {list_id} from {filename}")
            logger.info(f"   📊 Duplicates: {stats['duplicates']}, Invalid: {stats['invalid']}")
            return stats
            
        except Exception as e:
            logger.error(f"Error adding contacts: {e}", exc_info=True)
            return {"added": 0, "duplicates": 0, "invalid": 0}
    
    async def get_contacts(
        self,
        list_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get contacts from a list with pagination and filtering"""
        if not is_mongodb_available():
            return []
        
        try:
            contact_list = await self.get_list(list_id)
            if not contact_list:
                return []
            
            phones = contact_list.get("phones", [])
            
            # Filter by search if provided
            if search:
                phones = [p for p in phones if search.lower() in p.lower()]
            
            # Build result with consistent format
            result = []
            for i, phone in enumerate(phones):
                result.append({
                    "id": f"{list_id}_{i}",
                    "list_id": list_id,
                    "phone_number": phone,
                    "normalized_phone": phone,
                    "name": "",
                    "status": "active"
                })
            
            # Apply pagination
            return result[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return []
    
    async def get_active_contacts_for_campaign(self, list_id: str) -> List[str]:
        """Get all unique phone numbers for a campaign"""
        if not is_mongodb_available():
            return []
        
        try:
            contact_list = await self.get_list(list_id)
            if not contact_list:
                return []
            
            return contact_list.get("phones", [])
            
        except Exception as e:
            logger.error(f"Error getting active contacts: {e}")
            return []
    
    async def delete_contacts_by_phones(self, list_id: str, phone_numbers: List[str]) -> Dict[str, int]:
        """Remove phone numbers from a list
        
        Args:
            list_id: Contact list ID
            phone_numbers: List of phone numbers to remove
            
        Returns:
            {deleted: count, not_found: count}
        """
        if not is_mongodb_available():
            return {"deleted": 0, "not_found": 0}
        
        try:
            from utils.phone_validator import process_phone_list
            
            coll = self._get_collection()
            if coll is None:
                return {"deleted": 0, "not_found": 0}
            
            # Normalize incoming phone numbers
            processed = process_phone_list(phone_numbers)
            normalized_phones = set()
            for p in processed:
                if p.get("normalized") and p.get("status") == "active":
                    normalized_phones.add(p["normalized"])
            
            if not normalized_phones:
                return {"deleted": 0, "not_found": len(phone_numbers)}
            
            # Get current phones
            contact_list = await self.get_list(list_id)
            if not contact_list:
                return {"deleted": 0, "not_found": len(phone_numbers)}
            
            current_phones = set(contact_list.get("phones", []))
            phones_to_delete = normalized_phones & current_phones
            not_found = normalized_phones - current_phones
            
            if phones_to_delete:
                # Remove phones from array
                await coll.update_one(
                    {"_id": ObjectId(list_id)},
                    {
                        "$pull": {"phones": {"$in": list(phones_to_delete)}},
                        "$set": {
                            "contact_count": len(current_phones) - len(phones_to_delete),
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    }
                )
            
            logger.info(f"🗑️ Deleted {len(phones_to_delete)} contacts from list {list_id}")
            return {"deleted": len(phones_to_delete), "not_found": len(not_found)}
            
        except Exception as e:
            logger.error(f"Error deleting contacts: {e}", exc_info=True)
            return {"deleted": 0, "not_found": 0}
