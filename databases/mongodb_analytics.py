"""
MongoDB Analytics Module
Provides analytics and statistics for conversations and calls
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available
from config import MONGODB_CONVERSATIONS_COLLECTION

logger = logging.getLogger(__name__)

class MongoDBAnalytics:
    """Analytics queries for conversation and call data"""
    
    def __init__(self):
        self.collection_name = MONGODB_CONVERSATIONS_COLLECTION
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.collection_name]
    
    async def get_call_statistics(
        self,
        agent_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get overall call statistics"""
        if not is_mongodb_available():
            return {
                "total_calls": 0,
                "total_duration_seconds": 0,
                "average_duration_seconds": 0,
                "min_duration_seconds": 0,
                "max_duration_seconds": 0,
                "active_calls": 0,
                "completed_calls": 0,
            }
        
        try:
            collection = self._get_collection()
            if collection is None:
                return self._empty_stats()
            
            # Build query
            query = {}
            if agent_id:
                query["agent_id"] = agent_id
            if start_date or end_date:
                query["created_at"] = {}
                if start_date:
                    query["created_at"]["$gte"] = start_date.isoformat()
                if end_date:
                    query["created_at"]["$lte"] = end_date.isoformat()
            
            # Get all conversations
            cursor = collection.find(query)
            conversations = []
            async for doc in cursor:
                conversations.append(doc)
            
            # Calculate statistics
            total_calls = len(conversations)
            durations = []
            active_count = 0
            completed_count = 0
            
            for conv in conversations:
                # Calculate duration from created_at to updated_at
                created = datetime.fromisoformat(conv.get("created_at", datetime.utcnow().isoformat()))
                updated = datetime.fromisoformat(conv.get("updated_at", datetime.utcnow().isoformat()))
                duration = (updated - created).total_seconds()
                durations.append(duration)
                
                # Count by status
                status = conv.get("status", "active")
                if status == "active":
                    active_count += 1
                elif status == "completed":
                    completed_count += 1
            
            total_duration = sum(durations)
            avg_duration = total_duration / total_calls if total_calls > 0 else 0
            min_duration = min(durations) if durations else 0
            max_duration = max(durations) if durations else 0
            
            return {
                "total_calls": total_calls,
                "total_duration_seconds": round(total_duration, 2),
                "average_duration_seconds": round(avg_duration, 2),
                "min_duration_seconds": round(min_duration, 2),
                "max_duration_seconds": round(max_duration, 2),
                "active_calls": active_count,
                "completed_calls": completed_count,
            }
            
        except Exception as e:
            logger.error(f"Error getting call statistics: {e}")
            return self._empty_stats()
    
    async def get_calls_by_date(
        self,
        days: int = 7,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get call counts grouped by date"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Build query
            query = {
                "created_at": {
                    "$gte": start_date.isoformat(),
                    "$lte": end_date.isoformat()
                }
            }
            if agent_id:
                query["agent_id"] = agent_id
            
            # Aggregate by date
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {"$dateFromString": {"dateString": "$created_at"}}
                            }
                        },
                        "count": {"$sum": 1},
                        "total_duration": {
                            "$sum": {
                                "$subtract": [
                                    {"$dateFromString": {"dateString": "$updated_at"}},
                                    {"$dateFromString": {"dateString": "$created_at"}}
                                ]
                            }
                        }
                    }
                },
                {"$sort": {"_id": 1}}
            ]
            
            results = []
            async for doc in collection.aggregate(pipeline):
                results.append({
                    "date": doc["_id"],
                    "count": doc["count"],
                    "total_duration_seconds": doc.get("total_duration", 0) / 1000  # Convert ms to seconds
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting calls by date: {e}")
            return []
    
    async def get_calls_by_agent(self) -> List[Dict[str, Any]]:
        """Get call statistics grouped by agent/phone number"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Aggregate by agent_id
            pipeline = [
                {
                    "$group": {
                        "_id": "$agent_id",
                        "count": {"$sum": 1},
                        "total_duration": {
                            "$sum": {
                                "$subtract": [
                                    {"$dateFromString": {"dateString": "$updated_at"}},
                                    {"$dateFromString": {"dateString": "$created_at"}}
                                ]
                            }
                        },
                        "avg_duration": {
                            "$avg": {
                                "$subtract": [
                                    {"$dateFromString": {"dateString": "$updated_at"}},
                                    {"$dateFromString": {"dateString": "$created_at"}}
                                ]
                            }
                        }
                    }
                },
                {"$sort": {"count": -1}}
            ]
            
            results = []
            async for doc in collection.aggregate(pipeline):
                agent_id = doc["_id"] or "unknown"
                results.append({
                    "agent_id": agent_id,
                    "call_count": doc["count"],
                    "total_duration_seconds": round(doc.get("total_duration", 0) / 1000, 2),
                    "average_duration_seconds": round(doc.get("avg_duration", 0) / 1000, 2),
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting calls by agent: {e}")
            return []
    
    async def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent calls with details"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            cursor = collection.find().sort("created_at", -1).limit(limit)
            calls = []
            
            async for doc in cursor:
                created = datetime.fromisoformat(doc.get("created_at", datetime.utcnow().isoformat()))
                updated = datetime.fromisoformat(doc.get("updated_at", datetime.utcnow().isoformat()))
                duration = (updated - created).total_seconds()
                
                calls.append({
                    "session_id": doc.get("session_id"),
                    "agent_id": doc.get("agent_id"),
                    "customer_id": doc.get("customer_id"),
                    "status": doc.get("status", "active"),
                    "message_count": len(doc.get("messages", [])),
                    "duration_seconds": round(duration, 2),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                })
            
            return calls
            
        except Exception as e:
            logger.error(f"Error getting recent calls: {e}")
            return []
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics"""
        return {
            "total_calls": 0,
            "total_duration_seconds": 0,
            "average_duration_seconds": 0,
            "min_duration_seconds": 0,
            "max_duration_seconds": 0,
            "active_calls": 0,
            "completed_calls": 0,
        }

