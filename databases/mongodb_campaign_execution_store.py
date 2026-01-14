"""
MongoDB Campaign Execution Store
Handles logging and retrieving campaign execution records (SMS, WhatsApp, Voice)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from bson import ObjectId
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)


class MongoDBCampaignExecutionStore:
    """Store and retrieve campaign execution logs from MongoDB"""
    
    def __init__(self):
        self.collection_name = "campaign_executions"
    
    def _get_collection(self):
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.collection_name]
    
    async def log_execution(
        self,
        campaign_id: str,
        campaign_name: str,
        exec_type: str,  # "sms", "whatsapp", "voice"
        from_number: str,
        to_number: str,
        status: str,  # "sent", "failed", "called"
        message_sid: Optional[str] = None,
        call_sid: Optional[str] = None,
        contact_name: Optional[str] = None,
        error: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Log a campaign execution attempt"""
        if not is_mongodb_available():
            logger.warning("MongoDB not available, skipping execution log")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            now = datetime.utcnow().isoformat()
            
            doc = {
                "campaign_id": ObjectId(campaign_id) if isinstance(campaign_id, str) else campaign_id,
                "campaign_name": campaign_name,
                "type": exec_type,
                "from_number": from_number,
                "to_number": to_number,
                "contact_name": contact_name or "",
                "status": status,
                "message_sid": message_sid,
                "call_sid": call_sid,
                "error": error,
                "userId": user_id,
                "executed_at": now,
                "created_at": now
            }
            
            await collection.insert_one(doc)
            logger.info(f"📝 Logged campaign execution: {campaign_name} -> {to_number} ({status})")
            return True
            
        except Exception as e:
            logger.error(f"Error logging campaign execution: {e}", exc_info=True)
            return False
    
    async def get_executions(
        self,
        campaign_id: str,
        exec_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get execution logs for a campaign"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            query = {"campaign_id": ObjectId(campaign_id)}
            if exec_type:
                query["type"] = exec_type
            if status:
                query["status"] = status
            
            result = []
            cursor = collection.find(query).sort("executed_at", -1).skip(offset).limit(limit)
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                doc["campaign_id"] = str(doc["campaign_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting campaign executions: {e}")
            return []
    
    async def get_executions_for_user(
        self,
        user_id: str,
        exec_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all execution logs for a user"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            query = {"userId": user_id}
            if exec_type:
                query["type"] = exec_type
            
            result = []
            cursor = collection.find(query).sort("executed_at", -1).limit(limit)
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                doc["campaign_id"] = str(doc["campaign_id"])
                del doc["_id"]
                result.append(doc)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user executions: {e}")
            return []
    
    async def get_execution_stats(self, campaign_id: str) -> Dict[str, int]:
        """Get aggregated stats for a campaign's executions"""
        if not is_mongodb_available():
            return {"sent": 0, "failed": 0, "called": 0, "total": 0}
        
        try:
            collection = self._get_collection()
            if collection is None:
                return {"sent": 0, "failed": 0, "called": 0, "total": 0}
            
            pipeline = [
                {"$match": {"campaign_id": ObjectId(campaign_id)}},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            stats = {"sent": 0, "failed": 0, "called": 0, "total": 0}
            async for doc in collection.aggregate(pipeline):
                status = doc["_id"]
                count = doc["count"]
                stats["total"] += count
                if status in stats:
                    stats[status] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting execution stats: {e}")
            return {"sent": 0, "failed": 0, "called": 0, "total": 0}
