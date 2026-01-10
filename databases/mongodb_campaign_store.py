"""
MongoDB Campaign Store
Handles saving and loading campaigns and campaign items
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from bson import ObjectId
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)


class MongoDBCampaignStore:
    """Store and retrieve campaigns from MongoDB"""
    
    def __init__(self):
        self.campaigns_collection = "campaigns"
        self.items_collection = "campaign_items"
    
    def _get_campaigns_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.campaigns_collection]
    
    def _get_items_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.items_collection]
    
    # ==================== CAMPAIGN METHODS ====================
    
    async def create_campaign(self, campaign_data: Dict[str, Any], user_id: str) -> Optional[str]:
        """Create a new campaign
        
        Args:
            campaign_data: {
                name: string,
                type: "voice" | "sms" | "whatsapp",
                config: { promptId, messageBody, fromNumber },
                phone_numbers: list of phone numbers (optional if contact_list_id provided)
                contact_list_id: str (optional - use contacts from this list)
            }
            user_id: User ID for multi-tenancy
        
        Returns:
            Campaign ID if successful, None otherwise
        """
        if not is_mongodb_available():
            logger.warning("MongoDB not available")
            return None
        
        try:
            campaigns = self._get_campaigns_collection()
            if campaigns is None:
                return None
            
            phone_numbers = campaign_data.pop("phone_numbers", [])
            contact_list_id = campaign_data.get("contact_list_id")
            
            # If contact_list_id provided, fetch active contacts from that list
            if contact_list_id and not phone_numbers:
                from .mongodb_contact_list_store import MongoDBContactListStore
                contact_store = MongoDBContactListStore()
                phone_numbers = await contact_store.get_active_contacts_for_campaign(contact_list_id)
                logger.info(f"Fetched {len(phone_numbers)} contacts from list {contact_list_id}")
            
            # Check for scheduled_at
            scheduled_at = campaign_data.get("scheduled_at")
            initial_status = "scheduled" if scheduled_at else "draft"
            
            # Create campaign document
            campaign_doc = {
                "name": campaign_data.get("name", "Untitled Campaign"),
                "type": campaign_data.get("type", "sms"),
                "status": initial_status,
                "config": campaign_data.get("config", {}),
                "contact_list_id": contact_list_id,
                "scheduled_at": scheduled_at,
                "progress_percent": 0.0,
                "last_processed_at": None,
                "stats": {
                    "total": len(phone_numbers),
                    "pending": len(phone_numbers),
                    "sent": 0,
                    "failed": 0
                },
                "userId": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "isDeleted": False
            }
            
            result = await campaigns.insert_one(campaign_doc)
            campaign_id = str(result.inserted_id)
            
            # Create optimized queue (array-based instead of per-item docs)
            if phone_numbers:
                from .mongodb_campaign_queue_store import MongoDBCampaignQueueStore
                queue_store = MongoDBCampaignQueueStore()
                await queue_store.create_queue(campaign_id, phone_numbers)
            
            logger.info(f"✅ Created campaign {campaign_id} with {len(phone_numbers)} contacts (optimized queue)")
            return str(campaign_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating campaign: {e}", exc_info=True)
            return None
    
    async def get_campaign(self, campaign_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a campaign by ID"""
        if not is_mongodb_available():
            return None
        
        try:
            campaigns = self._get_campaigns_collection()
            if campaigns is None:
                return None
            
            query = {"_id": ObjectId(campaign_id), "isDeleted": {"$ne": True}}
            if user_id:
                query["userId"] = user_id
            
            doc = await campaigns.find_one(query)
            if doc:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                return doc
            return None
            
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            return None
    
    async def list_campaigns(
        self,
        user_id: Optional[str] = None,
        campaign_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List campaigns with optional filters"""
        if not is_mongodb_available():
            return []
        
        try:
            campaigns = self._get_campaigns_collection()
            if campaigns is None:
                return []
            
            query = {"isDeleted": {"$ne": True}}
            if user_id:
                query["userId"] = user_id
            if campaign_type:
                query["type"] = campaign_type
            if status:
                query["status"] = status
            
            result = []
            async for doc in campaigns.find(query).sort("created_at", -1):
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing campaigns: {e}")
            return []
    
    async def update_campaign(self, campaign_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a campaign"""
        if not is_mongodb_available():
            return False
        
        try:
            campaigns = self._get_campaigns_collection()
            if campaigns is None:
                return False
            
            update_data["updated_at"] = datetime.utcnow().isoformat()
            result = await campaigns.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating campaign {campaign_id}: {e}")
            return False
    
    async def delete_campaign(self, campaign_id: str, user_id: Optional[str] = None) -> bool:
        """Soft delete a campaign"""
        if not is_mongodb_available():
            return False
        
        try:
            campaigns = self._get_campaigns_collection()
            if campaigns is None:
                return False
            
            query = {"_id": ObjectId(campaign_id)}
            if user_id:
                query["userId"] = user_id
            
            result = await campaigns.update_one(
                query,
                {"$set": {"isDeleted": True, "updated_at": datetime.utcnow().isoformat()}}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting campaign {campaign_id}: {e}")
            return False
    
    # ==================== CAMPAIGN ITEMS METHODS ====================
    
    async def get_campaign_items(
        self,
        campaign_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get items for a campaign"""
        if not is_mongodb_available():
            return []
        
        try:
            items = self._get_items_collection()
            if items is None:
                return []
            
            query = {"campaign_id": ObjectId(campaign_id)}
            if status:
                query["status"] = status
            
            result = []
            cursor = items.find(query).skip(offset).limit(limit)
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                doc["campaign_id"] = str(doc["campaign_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting campaign items: {e}")
            return []
    
    async def get_pending_items(self, campaign_id: str, batch_size: int = 20) -> List[Dict[str, Any]]:
        """Get pending items for processing (legacy - use acquire_pending_items for atomic locking)"""
        return await self.get_campaign_items(campaign_id, status="pending", limit=batch_size)
    
    async def acquire_pending_items(self, campaign_id: str, batch_size: int = 10) -> List[Dict[str, Any]]:
        """Atomically acquire pending items by locking them (pending -> in_progress).
        
        This prevents duplicate processing even with multiple workers or pod restarts.
        Uses find_one_and_update for each item to ensure atomic state transition.
        
        Returns:
            List of locked items ready for processing
        """
        if not is_mongodb_available():
            return []
        
        try:
            items = self._get_items_collection()
            if items is None:
                return []
            
            locked_items = []
            now = datetime.utcnow().isoformat()
            
            # Atomically lock items one by one until we have batch_size or no more pending
            for _ in range(batch_size):
                doc = await items.find_one_and_update(
                    {
                        "campaign_id": ObjectId(campaign_id),
                        "status": "pending"
                    },
                    {
                        "$set": {
                            "status": "in_progress",
                            "locked_at": now,
                            "updated_at": now
                        }
                    },
                    return_document=True  # Return the updated document
                )
                
                if doc is None:
                    # No more pending items
                    break
                
                # Convert ObjectIds to strings
                doc["id"] = str(doc["_id"])
                doc["campaign_id"] = str(doc["campaign_id"])
                del doc["_id"]
                locked_items.append(doc)
            
            if locked_items:
                logger.info(f"🔒 Acquired {len(locked_items)} items for campaign {campaign_id}")
            
            return locked_items
            
        except Exception as e:
            logger.error(f"Error acquiring pending items: {e}", exc_info=True)
            return []
    
    async def update_item_status(
        self,
        item_id: str,
        status: str,
        result: Optional[str] = None
    ) -> bool:
        """Update status of a campaign item"""
        if not is_mongodb_available():
            return False
        
        try:
            items = self._get_items_collection()
            if items is None:
                return False
            
            update = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            if result:
                update["result"] = result
            
            res = await items.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": update}
            )
            return res.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating item {item_id}: {e}")
            return False
    
    async def update_campaign_stats(self, campaign_id: str) -> bool:
        """Recalculate and update campaign stats"""
        if not is_mongodb_available():
            return False
        
        try:
            items = self._get_items_collection()
            campaigns = self._get_campaigns_collection()
            if items is None or campaigns is None:
                return False
            
            pipeline = [
                {"$match": {"campaign_id": ObjectId(campaign_id)}},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            stats = {"total": 0, "pending": 0, "sent": 0, "failed": 0}
            async for doc in items.aggregate(pipeline):
                status = doc["_id"]
                count = doc["count"]
                stats["total"] += count
                if status == "pending":
                    stats["pending"] = count
                elif status == "sent":
                    stats["sent"] = count
                elif status == "failed":
                    stats["failed"] = count
            
            # Calculate progress percentage
            progress = 0.0
            if stats["total"] > 0:
                progress = ((stats["sent"] + stats["failed"]) / stats["total"]) * 100
            
            await campaigns.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {
                    "stats": stats,
                    "progress_percent": progress,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            return True
            
        except Exception as e:
            logger.error(f"Error updating campaign stats: {e}")
            return False
    
    async def schedule_campaign(self, campaign_id: str, scheduled_at: str, user_id: Optional[str] = None) -> bool:
        """Schedule a draft campaign for future execution"""
        if not is_mongodb_available():
            return False
        
        try:
            campaigns = self._get_campaigns_collection()
            if campaigns is None:
                return False
            
            query = {"_id": ObjectId(campaign_id), "status": "draft"}
            if user_id:
                query["userId"] = user_id
            
            result = await campaigns.update_one(
                query,
                {"$set": {
                    "status": "scheduled",
                    "scheduled_at": scheduled_at,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"📅 Scheduled campaign {campaign_id} for {scheduled_at}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error scheduling campaign {campaign_id}: {e}")
            return False
    
    async def get_ready_scheduled_campaigns(self) -> List[Dict[str, Any]]:
        """Get scheduled campaigns that are ready to run (scheduled_at <= now)"""
        if not is_mongodb_available():
            return []
        
        try:
            campaigns = self._get_campaigns_collection()
            if campaigns is None:
                return []
            
            now = datetime.utcnow().isoformat()
            
            query = {
                "status": "scheduled",
                "scheduled_at": {"$lte": now},
                "isDeleted": {"$ne": True}
            }
            
            result = []
            async for doc in campaigns.find(query):
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting ready scheduled campaigns: {e}")
            return []
    
    async def reset_in_progress_items(self, campaign_id: str) -> int:
        """Reset any in_progress items back to pending (crash recovery)"""
        if not is_mongodb_available():
            return 0
        
        try:
            items = self._get_items_collection()
            if items is None:
                return 0
            
            result = await items.update_many(
                {"campaign_id": ObjectId(campaign_id), "status": "in_progress"},
                {"$set": {"status": "pending", "updated_at": datetime.utcnow().isoformat()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"🔄 Reset {result.modified_count} in_progress items to pending for campaign {campaign_id}")
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error resetting in_progress items: {e}")
            return 0
