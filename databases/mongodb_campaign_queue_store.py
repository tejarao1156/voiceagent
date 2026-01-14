"""
MongoDB Campaign Queue Store
Optimized storage for large campaigns (100k+ contacts)
Uses array-based storage instead of per-item documents
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from bson import ObjectId
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

# MongoDB document size limit is 16MB, ~50k phone numbers per doc is safe
MAX_PHONES_PER_DOC = 50000


class MongoDBCampaignQueueStore:
    """Optimized queue storage for large campaigns"""
    
    def __init__(self):
        self.queue_collection = "campaign_queue"
        self.results_collection = "campaign_results"
    
    def _get_queue_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.queue_collection]
    
    def _get_results_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.results_collection]
    
    async def create_queue(self, campaign_id: str, phone_numbers: List[str]) -> bool:
        """Create queue document(s) for a campaign.
        
        For very large lists (>50k), creates multiple documents.
        """
        if not is_mongodb_available():
            return False
        
        try:
            queue = self._get_queue_collection()
            results = self._get_results_collection()
            if queue is None or results is None:
                return False
            
            now = datetime.utcnow().isoformat()
            campaign_oid = ObjectId(campaign_id)
            
            # Split into chunks if needed
            chunks = [phone_numbers[i:i + MAX_PHONES_PER_DOC] 
                      for i in range(0, len(phone_numbers), MAX_PHONES_PER_DOC)]
            
            # Create queue documents
            for idx, chunk in enumerate(chunks):
                await queue.insert_one({
                    "campaign_id": campaign_oid,
                    "chunk_index": idx,
                    "phones": chunk,
                    "cursor": 0,  # Index of next phone to process
                    "created_at": now
                })
            
            # Create results document
            await results.insert_one({
                "campaign_id": campaign_oid,
                "success": [],
                "failed": [],
                "total": len(phone_numbers),
                "processed": 0,
                "created_at": now,
                "updated_at": now
            })
            
            logger.info(f"📋 Created queue for campaign {campaign_id}: {len(phone_numbers)} phones in {len(chunks)} chunk(s)")
            return True
            
        except Exception as e:
            logger.error(f"Error creating campaign queue: {e}", exc_info=True)
            return False
    
    async def acquire_batch(self, campaign_id: str, batch_size: int = 10) -> List[str]:
        """Atomically acquire a batch of phones from the queue.
        
        Uses cursor increment for crash-safe processing.
        Returns list of phone numbers to process.
        """
        if not is_mongodb_available():
            return []
        
        try:
            queue = self._get_queue_collection()
            if queue is None:
                return []
            
            campaign_oid = ObjectId(campaign_id)
            
            # Find first non-exhausted chunk and get batch
            doc = await queue.find_one_and_update(
                {
                    "campaign_id": campaign_oid,
                    "$expr": {"$lt": ["$cursor", {"$size": "$phones"}]}
                },
                {
                    "$inc": {"cursor": batch_size}
                },
                return_document=False  # Return document BEFORE update
            )
            
            if doc is None:
                return []
            
            # Extract the batch from cursor position
            cursor = doc.get("cursor", 0)
            phones = doc.get("phones", [])
            batch = phones[cursor:cursor + batch_size]
            
            if batch:
                logger.info(f"🔒 Acquired {len(batch)} phones from campaign {campaign_id}")
            
            return batch
            
        except Exception as e:
            logger.error(f"Error acquiring batch: {e}", exc_info=True)
            return []
    
    async def record_result(self, campaign_id: str, phone: str, success: bool) -> bool:
        """Record a single result (success or failed)."""
        if not is_mongodb_available():
            return False
        
        try:
            results = self._get_results_collection()
            if results is None:
                return False
            
            field = "success" if success else "failed"
            await results.update_one(
                {"campaign_id": ObjectId(campaign_id)},
                {
                    "$push": {field: phone},
                    "$inc": {"processed": 1},
                    "$set": {"updated_at": datetime.utcnow().isoformat()}
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error recording result: {e}", exc_info=True)
            return False
    
    async def record_batch_results(
        self, 
        campaign_id: str, 
        success_phones: List[str], 
        failed_phones: List[str]
    ) -> bool:
        """Record multiple results at once (more efficient)."""
        if not is_mongodb_available():
            return False
        
        try:
            results = self._get_results_collection()
            if results is None:
                return False
            
            update = {
                "$inc": {"processed": len(success_phones) + len(failed_phones)},
                "$set": {"updated_at": datetime.utcnow().isoformat()}
            }
            
            if success_phones:
                update["$push"] = {"success": {"$each": success_phones}}
            if failed_phones:
                if "$push" in update:
                    update["$push"]["failed"] = {"$each": failed_phones}
                else:
                    update["$push"] = {"failed": {"$each": failed_phones}}
            
            await results.update_one(
                {"campaign_id": ObjectId(campaign_id)},
                update
            )
            return True
            
        except Exception as e:
            logger.error(f"Error recording batch results: {e}", exc_info=True)
            return False
    
    async def get_results(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign results summary."""
        if not is_mongodb_available():
            return None
        
        try:
            results = self._get_results_collection()
            if results is None:
                return None
            
            doc = await results.find_one({"campaign_id": ObjectId(campaign_id)})
            if doc:
                doc["id"] = str(doc["_id"])
                doc["campaign_id"] = str(doc["campaign_id"])
                del doc["_id"]
                # Return counts instead of full arrays for large campaigns
                doc["success_count"] = len(doc.get("success", []))
                doc["failed_count"] = len(doc.get("failed", []))
            return doc
            
        except Exception as e:
            logger.error(f"Error getting results: {e}", exc_info=True)
            return None
    
    async def get_queue_stats(self, campaign_id: str) -> Dict[str, int]:
        """Get queue processing stats."""
        if not is_mongodb_available():
            return {"total": 0, "processed": 0, "remaining": 0}
        
        try:
            queue = self._get_queue_collection()
            if queue is None:
                return {"total": 0, "processed": 0, "remaining": 0}
            
            pipeline = [
                {"$match": {"campaign_id": ObjectId(campaign_id)}},
                {"$group": {
                    "_id": None,
                    "total": {"$sum": {"$size": "$phones"}},
                    "processed": {"$sum": "$cursor"}
                }}
            ]
            
            result = {"total": 0, "processed": 0, "remaining": 0}
            async for doc in queue.aggregate(pipeline):
                result["total"] = doc.get("total", 0)
                result["processed"] = doc.get("processed", 0)
                result["remaining"] = result["total"] - result["processed"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}", exc_info=True)
            return {"total": 0, "processed": 0, "remaining": 0}
    
    async def reset_queue(self, campaign_id: str) -> bool:
        """Reset queue cursors for crash recovery."""
        if not is_mongodb_available():
            return False
        
        try:
            queue = self._get_queue_collection()
            results = self._get_results_collection()
            if queue is None or results is None:
                return False
            
            # Get already processed count from results
            result_doc = await results.find_one({"campaign_id": ObjectId(campaign_id)})
            if not result_doc:
                return False
            
            processed = result_doc.get("processed", 0)
            
            # Reset cursor to processed count (skip already done)
            # This is a simplified recovery - for perfect recovery,
            # we'd need to track which specific phones were processed
            await queue.update_many(
                {"campaign_id": ObjectId(campaign_id)},
                {"$set": {"cursor": 0}}  # Full reset, worker will re-process
            )
            
            logger.info(f"🔄 Reset queue for campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting queue: {e}", exc_info=True)
            return False
    
    async def delete_queue(self, campaign_id: str) -> bool:
        """Delete queue and results for a campaign."""
        if not is_mongodb_available():
            return False
        
        try:
            queue = self._get_queue_collection()
            results = self._get_results_collection()
            if queue is None or results is None:
                return False
            
            campaign_oid = ObjectId(campaign_id)
            await queue.delete_many({"campaign_id": campaign_oid})
            await results.delete_many({"campaign_id": campaign_oid})
            
            logger.info(f"🗑️ Deleted queue for campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting queue: {e}", exc_info=True)
            return False
