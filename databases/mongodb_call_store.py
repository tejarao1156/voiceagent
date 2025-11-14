"""
MongoDB Call Store
Handles storing and retrieving phone call records with real-time transcripts
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from .mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

class MongoDBCallStore:
    """Store and retrieve phone calls from MongoDB"""
    
    def __init__(self):
        self.collection_name = "calls"
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_mongo_db()
        if db is None:
            return None
        return db[self.collection_name]
    
    async def create_call(self, call_sid: str, from_number: str, to_number: str, 
                         agent_id: Optional[str] = None, session_id: Optional[str] = None) -> bool:
        """Create a new call record when call starts"""
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping call creation")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            now = datetime.utcnow().isoformat()
            
            call_doc = {
                "call_sid": call_sid,
                "from_number": from_number,
                "to_number": to_number,
                "agent_id": agent_id or to_number,
                "session_id": session_id or call_sid,
                "status": "active",
                "start_time": now,
                "end_time": None,
                "duration_seconds": None,
                "transcript": [],  # Array of {role, text, timestamp}
                "created_at": now,
                "updated_at": now,
            }
            
            await collection.insert_one(call_doc)
            logger.info(f"Created call record: {call_sid} from {from_number} to {to_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating call record: {e}")
            return False
    
    async def update_call_transcript(self, call_sid: str, role: str, text: str) -> bool:
        """Add real-time transcript entry to active call"""
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            timestamp = datetime.utcnow().isoformat()
            transcript_entry = {
                "role": role,  # "user" or "assistant"
                "text": text,
                "timestamp": timestamp
            }
            
            await collection.update_one(
                {"call_sid": call_sid},
                {
                    "$push": {"transcript": transcript_entry},
                    "$set": {"updated_at": timestamp}
                }
            )
            
            logger.info(f"✅ Updated transcript for call {call_sid}: {role} - {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error updating call transcript: {e}")
            return False
    
    async def end_call(self, call_sid: str, duration_seconds: Optional[float] = None) -> bool:
        """Mark call as completed and store final duration"""
        if not is_mongodb_available():
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            now = datetime.utcnow().isoformat()
            
            # If duration not provided, calculate from start_time
            if duration_seconds is None:
                call_doc = await collection.find_one({"call_sid": call_sid})
                if call_doc and call_doc.get("start_time"):
                    start_time = datetime.fromisoformat(call_doc["start_time"])
                    end_time = datetime.fromisoformat(now)
                    duration_seconds = (end_time - start_time).total_seconds()
            
            await collection.update_one(
                {"call_sid": call_sid},
                {
                    "$set": {
                        "status": "completed",
                        "end_time": now,
                        "duration_seconds": duration_seconds,
                        "updated_at": now
                    }
                }
            )
            
            logger.info(f"Ended call {call_sid}: duration {duration_seconds:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Error ending call: {e}")
            return False
    
    async def get_all_calls(self, agent_id: Optional[str] = None, 
                           status: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get all calls with transcripts"""
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            query = {}
            if agent_id:
                query["agent_id"] = agent_id
            if status:
                query["status"] = status
            
            cursor = collection.find(query).sort("created_at", -1).limit(limit)
            calls = []
            
            async for doc in cursor:
                if "_id" in doc:
                    del doc["_id"]
                
                # Convert transcript to conversation format for UI
                transcript = doc.get("transcript", [])
                conversation = [
                    {
                        "role": msg.get("role"),
                        "text": msg.get("text"),
                        "timestamp": msg.get("timestamp")
                    }
                    for msg in transcript
                ]
                
                calls.append({
                    "id": doc.get("call_sid"),
                    "call_sid": doc.get("call_sid"),
                    "from_number": doc.get("from_number"),
                    "to_number": doc.get("to_number"),
                    "agent_id": doc.get("agent_id"),
                    "session_id": doc.get("session_id"),
                    "status": "ongoing" if doc.get("status") == "active" else "finished",
                    "timestamp": doc.get("start_time"),
                    "duration": doc.get("duration_seconds"),
                    "conversation": conversation,
                    "callerNumber": doc.get("from_number"),  # Add for UI compatibility
                })
            
            return calls
            
        except Exception as e:
            logger.error(f"Error getting calls: {e}")
            return []
    
    async def get_active_calls(self) -> List[Dict[str, Any]]:
        """Get currently active calls for real-time display"""
        return await self.get_all_calls(status="active", limit=50)
    
    async def get_call_by_sid(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """Get a specific call by call_sid"""
        if not is_mongodb_available():
            return None
        
        try:
            collection = self._get_collection()
            if collection is None:
                return None
            
            doc = await collection.find_one({"call_sid": call_sid})
            if doc is None:
                return None
            
            if "_id" in doc:
                del doc["_id"]
            
            # Convert transcript to conversation format
            transcript = doc.get("transcript", [])
            conversation = [
                {
                    "role": msg.get("role"),
                    "text": msg.get("text"),
                    "timestamp": msg.get("timestamp")
                }
                for msg in transcript
            ]
            
            return {
                "id": doc.get("call_sid"),
                "call_sid": doc.get("call_sid"),
                "from_number": doc.get("from_number"),
                "to_number": doc.get("to_number"),
                "agent_id": doc.get("agent_id"),
                "session_id": doc.get("session_id"),
                "status": "ongoing" if doc.get("status") == "active" else "finished",
                "timestamp": doc.get("start_time"),
                "duration": doc.get("duration_seconds"),
                "conversation": conversation,
                "callerNumber": doc.get("from_number"),  # Add for UI compatibility
            }
            
        except Exception as e:
            logger.error(f"Error getting call by sid: {e}")
            return None

