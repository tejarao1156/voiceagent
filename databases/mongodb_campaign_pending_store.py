"""
MongoDB Campaign Pending Store
Tracks pending campaign items (voice calls) waiting for completion via webhook
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import logging
from bson import ObjectId
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)


class MongoDBCampaignPendingStore:
    """Track pending campaign items waiting for completion"""
    
    def __init__(self):
        self.collection_name = "campaign_pending_items"
    
    def _get_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.collection_name]
    
    async def create_pending(
        self, 
        campaign_id: str, 
        phone: str, 
        item_type: str,  # "voice", "sms", "whatsapp"
        sid: str  # call_sid or message_sid
    ) -> Optional[str]:
        """Create a pending item to track"""
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            doc = {
                "campaign_id": ObjectId(campaign_id),
                "phone": phone,
                "type": item_type,
                "sid": sid,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": None
            }
            
            result = await collection.insert_one(doc)
            logger.debug(f"📋 Created pending item for {sid}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating pending item: {e}", exc_info=True)
            return None
    
    async def mark_completed(self, sid: str, status: str = "completed") -> bool:
        """Mark a pending item as completed (called by webhook)"""
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            result = await collection.update_one(
                {"sid": sid, "status": "pending"},
                {
                    "$set": {
                        "status": status,
                        "completed_at": datetime.utcnow().isoformat()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Marked {sid} as {status}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error marking item completed: {e}", exc_info=True)
            return False
    
    async def get_pending_count(self, campaign_id: str) -> int:
        """Get count of pending items for a campaign"""
        if not is_mongodb_available():
            return 0
        
        try:
            collection = self._get_collection()
            if collection is None:
                return 0
            
            count = await collection.count_documents({
                "campaign_id": ObjectId(campaign_id),
                "status": "pending"
            })
            return count
            
        except Exception as e:
            logger.error(f"Error getting pending count: {e}", exc_info=True)
            return 0
    
    async def wait_for_completion(
        self, 
        campaign_id: str, 
        timeout_seconds: int = 300,
        poll_interval: float = 2.0
    ) -> Dict[str, int]:
        """Wait for all pending items in a batch to complete
        
        Returns: {"completed": N, "failed": N, "timed_out": N}
        """
        if not is_mongodb_available():
            return {"completed": 0, "failed": 0, "timed_out": 0}
        
        start_time = datetime.utcnow()
        
        while True:
            pending_count = await self.get_pending_count(campaign_id)
            
            if pending_count == 0:
                # All items completed
                break
            
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= timeout_seconds:
                logger.warning(f"⏰ Timeout waiting for {pending_count} pending items in campaign {campaign_id}")
                # Mark remaining as timed_out
                await self._timeout_pending(campaign_id)
                break
            
            logger.debug(f"⏳ Waiting for {pending_count} pending items (elapsed: {elapsed:.1f}s)")
            await asyncio.sleep(poll_interval)
        
        # Get final stats
        return await self._get_batch_stats(campaign_id)
    
    async def _timeout_pending(self, campaign_id: str):
        """Mark all remaining pending items as timed_out"""
        try:
            collection = self._get_collection()
            if collection is None:
                return
            
            await collection.update_many(
                {"campaign_id": ObjectId(campaign_id), "status": "pending"},
                {
                    "$set": {
                        "status": "timed_out",
                        "completed_at": datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error timing out pending items: {e}")
    
    async def _get_batch_stats(self, campaign_id: str) -> Dict[str, int]:
        """Get stats for completed batch"""
        try:
            collection = self._get_collection()
            if collection is None:
                return {"completed": 0, "failed": 0, "timed_out": 0}
            
            pipeline = [
                {"$match": {"campaign_id": ObjectId(campaign_id)}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            
            stats = {"completed": 0, "failed": 0, "timed_out": 0, "pending": 0}
            async for doc in collection.aggregate(pipeline):
                status = doc["_id"]
                if status in stats:
                    stats[status] = doc["count"]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting batch stats: {e}")
            return {"completed": 0, "failed": 0, "timed_out": 0}
    
    async def clear_campaign_pending(self, campaign_id: str):
        """Clear all pending items for a campaign (cleanup)"""
        try:
            collection = self._get_collection()
            if collection is None:
                return
            
            await collection.delete_many({"campaign_id": ObjectId(campaign_id)})
            
        except Exception as e:
            logger.error(f"Error clearing pending items: {e}")
