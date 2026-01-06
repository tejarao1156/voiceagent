"""
MongoDB Contact List Store
Handles saving and loading contact lists, contacts, and versions
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from bson import ObjectId
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)


class MongoDBContactListStore:
    """Store and retrieve contact lists from MongoDB"""
    
    def __init__(self):
        self.lists_collection = "contact_lists"
        self.contacts_collection = "contacts"
        self.versions_collection = "contact_list_versions"
    
    def _get_lists_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.lists_collection]
    
    def _get_contacts_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.contacts_collection]
    
    def _get_versions_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.versions_collection]
    
    # ==================== CONTACT LIST METHODS ====================
    
    async def create_list(self, name: str, user_id: str, description: str = "") -> Optional[str]:
        """Create a new empty contact list"""
        if not is_mongodb_available():
            return None
        
        try:
            lists = self._get_lists_collection()
            if lists is None:
                return None
            
            doc = {
                "name": name,
                "description": description,
                "version": 1,
                "contact_count": 0,
                "userId": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "isDeleted": False
            }
            
            result = await lists.insert_one(doc)
            list_id = str(result.inserted_id)
            
            # Create initial version
            await self._create_version(list_id, 1, {"added": 0, "updated": 0, "removed": 0}, 0)
            
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
            lists = self._get_lists_collection()
            if lists is None:
                return None
            
            query = {"_id": ObjectId(list_id), "isDeleted": {"$ne": True}}
            if user_id:
                query["userId"] = user_id
            
            doc = await lists.find_one(query)
            if doc:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
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
            lists = self._get_lists_collection()
            if lists is None:
                return []
            
            result = []
            async for doc in lists.find({"userId": user_id, "isDeleted": {"$ne": True}}).sort("updated_at", -1):
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
            lists = self._get_lists_collection()
            if lists is None:
                return False
            
            query = {"_id": ObjectId(list_id)}
            if user_id:
                query["userId"] = user_id
            
            update_data["updated_at"] = datetime.utcnow().isoformat()
            result = await lists.update_one(query, {"$set": update_data})
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating contact list: {e}")
            return False
    
    async def delete_list(self, list_id: str, user_id: Optional[str] = None) -> bool:
        """Soft delete a contact list"""
        if not is_mongodb_available():
            return False
        
        try:
            lists = self._get_lists_collection()
            if lists is None:
                return False
            
            query = {"_id": ObjectId(list_id)}
            if user_id:
                query["userId"] = user_id
            
            result = await lists.update_one(
                query,
                {"$set": {"isDeleted": True, "updated_at": datetime.utcnow().isoformat()}}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting contact list: {e}")
            return False
    
    # ==================== CONTACTS METHODS ====================
    
    async def add_contacts(self, list_id: str, contacts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Add multiple contacts to a list with duplicate detection"""
        if not is_mongodb_available():
            return {"added": 0, "duplicates": 0, "invalid": 0}
        
        try:
            contacts_coll = self._get_contacts_collection()
            if contacts_coll is None:
                return {"added": 0, "duplicates": 0, "invalid": 0}
            
            # Get existing normalized numbers
            existing = set()
            async for doc in contacts_coll.find(
                {"list_id": ObjectId(list_id), "isDeleted": {"$ne": True}},
                {"normalized_phone": 1}
            ):
                existing.add(doc.get("normalized_phone"))
            
            stats = {"added": 0, "duplicates": 0, "invalid": 0}
            docs_to_insert = []
            
            for contact in contacts:
                normalized = contact.get("normalized")
                status = contact.get("status", "active")
                
                if status == "invalid":
                    stats["invalid"] += 1
                    continue
                
                if not normalized:
                    stats["invalid"] += 1
                    continue
                
                if normalized in existing:
                    stats["duplicates"] += 1
                    continue
                
                existing.add(normalized)
                docs_to_insert.append({
                    "list_id": ObjectId(list_id),
                    "phone_number": contact.get("original", normalized),
                    "normalized_phone": normalized,
                    "name": contact.get("name", ""),
                    "metadata": contact.get("metadata", {}),
                    "status": status,
                    "created_at": datetime.utcnow().isoformat(),
                    "isDeleted": False
                })
            
            if docs_to_insert:
                await contacts_coll.insert_many(docs_to_insert)
                stats["added"] = len(docs_to_insert)
            
            # Update list contact count
            await self._update_list_count(list_id)
            
            # Increment version
            await self._increment_version(list_id, stats)
            
            logger.info(f"✅ Added {stats['added']} contacts to list {list_id}")
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
            contacts = self._get_contacts_collection()
            if contacts is None:
                return []
            
            query = {"list_id": ObjectId(list_id), "isDeleted": {"$ne": True}}
            
            if status:
                query["status"] = status
            
            if search:
                query["$or"] = [
                    {"phone_number": {"$regex": search, "$options": "i"}},
                    {"name": {"$regex": search, "$options": "i"}}
                ]
            
            result = []
            cursor = contacts.find(query).skip(offset).limit(limit).sort("created_at", -1)
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                doc["list_id"] = str(doc["list_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return []
    
    async def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get a single contact by ID"""
        if not is_mongodb_available():
            return None
        
        try:
            contacts = self._get_contacts_collection()
            if contacts is None:
                return None
            
            doc = await contacts.find_one({"_id": ObjectId(contact_id), "isDeleted": {"$ne": True}})
            if doc:
                doc["id"] = str(doc["_id"])
                doc["list_id"] = str(doc["list_id"])
                del doc["_id"]
                return doc
            return None
            
        except Exception as e:
            logger.error(f"Error getting contact: {e}")
            return None
    
    async def update_contact(self, contact_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a contact"""
        if not is_mongodb_available():
            return False
        
        try:
            contacts = self._get_contacts_collection()
            if contacts is None:
                return False
            
            update_data["updated_at"] = datetime.utcnow().isoformat()
            result = await contacts.update_one(
                {"_id": ObjectId(contact_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                # Get list_id and increment version
                contact = await self.get_contact(contact_id)
                if contact:
                    await self._increment_version(contact["list_id"], {"added": 0, "updated": 1, "removed": 0})
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return False
    
    async def delete_contact(self, contact_id: str) -> bool:
        """Soft delete a contact"""
        if not is_mongodb_available():
            return False
        
        try:
            contacts = self._get_contacts_collection()
            if contacts is None:
                return False
            
            # Get contact first for list_id
            contact = await self.get_contact(contact_id)
            if not contact:
                return False
            
            result = await contacts.update_one(
                {"_id": ObjectId(contact_id)},
                {"$set": {"isDeleted": True, "updated_at": datetime.utcnow().isoformat()}}
            )
            
            if result.modified_count > 0:
                await self._update_list_count(contact["list_id"])
                await self._increment_version(contact["list_id"], {"added": 0, "updated": 0, "removed": 1})
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting contact: {e}")
            return False
    
    async def get_active_contacts_for_campaign(self, list_id: str) -> List[str]:
        """Get only active (valid) phone numbers for a campaign"""
        if not is_mongodb_available():
            return []
        
        try:
            contacts = self._get_contacts_collection()
            if contacts is None:
                return []
            
            result = []
            async for doc in contacts.find({
                "list_id": ObjectId(list_id),
                "status": "active",
                "isDeleted": {"$ne": True}
            }):
                result.append(doc.get("normalized_phone") or doc.get("phone_number"))
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting active contacts: {e}")
            return []
    
    # ==================== VERSION METHODS ====================
    
    async def _create_version(self, list_id: str, version: int, changes: Dict, count: int):
        """Create a version record"""
        try:
            versions = self._get_versions_collection()
            if versions is None:
                return
            
            await versions.insert_one({
                "list_id": ObjectId(list_id),
                "version": version,
                "changes": changes,
                "snapshot_count": count,
                "created_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error creating version: {e}")
    
    async def _increment_version(self, list_id: str, changes: Dict):
        """Increment version and create version record"""
        try:
            lists = self._get_lists_collection()
            if lists is None:
                return
            
            # Get current state
            list_doc = await self.get_list(list_id)
            if not list_doc:
                return
            
            new_version = list_doc.get("version", 1) + 1
            new_count = list_doc.get("contact_count", 0)
            
            # Update list version
            await lists.update_one(
                {"_id": ObjectId(list_id)},
                {"$set": {"version": new_version, "updated_at": datetime.utcnow().isoformat()}}
            )
            
            # Create version record
            await self._create_version(list_id, new_version, changes, new_count)
            
        except Exception as e:
            logger.error(f"Error incrementing version: {e}")
    
    async def _update_list_count(self, list_id: str):
        """Update contact count on list"""
        try:
            contacts = self._get_contacts_collection()
            lists = self._get_lists_collection()
            if contacts is None or lists is None:
                return
            
            count = await contacts.count_documents({
                "list_id": ObjectId(list_id),
                "isDeleted": {"$ne": True}
            })
            
            await lists.update_one(
                {"_id": ObjectId(list_id)},
                {"$set": {"contact_count": count, "updated_at": datetime.utcnow().isoformat()}}
            )
            
        except Exception as e:
            logger.error(f"Error updating list count: {e}")
    
    async def get_versions(self, list_id: str) -> List[Dict[str, Any]]:
        """Get version history for a list"""
        if not is_mongodb_available():
            return []
        
        try:
            versions = self._get_versions_collection()
            if versions is None:
                return []
            
            result = []
            async for doc in versions.find({"list_id": ObjectId(list_id)}).sort("version", -1):
                doc["id"] = str(doc["_id"])
                doc["list_id"] = str(doc["list_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting versions: {e}")
            return []
