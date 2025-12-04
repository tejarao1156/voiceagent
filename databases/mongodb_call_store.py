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
        """Get MongoDB collection - creates collection if it doesn't exist"""
        db = get_mongo_db()
        if db is None:
            logger.warning(f"MongoDB database not available, cannot get collection '{self.collection_name}'")
            return None
        # Accessing the collection will create it if it doesn't exist (MongoDB auto-creates)
        try:
            collection = db[self.collection_name]
            logger.debug(f"Accessed MongoDB collection '{self.collection_name}'")
            return collection
        except Exception as e:
            logger.error(f"Error accessing collection '{self.collection_name}': {e}", exc_info=True)
            return None
    
    async def create_call(self, call_sid: str, from_number: str, to_number: str, 
                         agent_id: Optional[str] = None, session_id: Optional[str] = None,
                         scheduled_call_id: Optional[str] = None, is_scheduled: bool = False) -> bool:
        """Create a new call record when call starts
        
        Handles edge cases:
        - Duplicate call_sid (race condition)
        - MongoDB unavailable
        - Missing required fields
        """
        if not is_mongodb_available():
            logger.debug("MongoDB not available, skipping call creation")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            
            # EDGE CASE 1: Check if call already exists (race condition with status webhook)
            existing = await collection.find_one({"call_sid": call_sid})
            if existing:
                logger.info(f"ℹ️ Call record for {call_sid} already exists, skipping creation")
                return True  # Return True - record exists, that's fine
            
            # EDGE CASE 2: Validate required fields
            if not call_sid:
                logger.error("Cannot create call record: call_sid is required")
                return False
            
            now = datetime.utcnow().isoformat()
            
            call_doc = {
                "call_sid": call_sid,
                "from_number": from_number or "unknown",
                "to_number": to_number or "unknown",
                "agent_id": agent_id or to_number or "unknown",
                "session_id": session_id or call_sid,
                "status": "active",
                "start_time": now,
                "end_time": None,
                "duration_seconds": None,
                "transcript": [],  # Array of {role, text, timestamp}
                "created_at": now,
                "updated_at": now,
                "scheduled_call_id": scheduled_call_id,
                "is_scheduled": is_scheduled
            }
            
            await collection.insert_one(call_doc)
            logger.info(f"Created call record: {call_sid} from {from_number} to {to_number} (Scheduled: {is_scheduled})")
            return True
            
        except Exception as e:
            # EDGE CASE 3: Duplicate key error (race condition)
            if "duplicate" in str(e).lower() or "E11000" in str(e):
                logger.info(f"ℹ️ Call record for {call_sid} already exists (duplicate key error - race condition)")
                return True  # Return True - record exists, that's fine
            else:
                logger.error(f"Error creating call record: {e}", exc_info=True)
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
        """Mark call as completed and store final duration
        
        Handles edge cases:
        - Call already completed (idempotent)
        - Missing call record
        - Invalid duration calculation
        - MongoDB connection issues
        - Race conditions
        """
        if not is_mongodb_available():
            logger.warning(f"MongoDB not available, cannot end call {call_sid}")
            return False
        
        try:
            collection = self._get_collection()
            if collection is None:
                logger.warning(f"MongoDB collection not available, cannot end call {call_sid}")
                return False
            
            # EDGE CASE 1: Check if call exists
            call_doc = await collection.find_one({"call_sid": call_sid})
            if not call_doc:
                logger.warning(f"Call {call_sid} not found in MongoDB - may have been created before call record was saved")
                return False
            
            # EDGE CASE 2: Call already completed (idempotent operation)
            if call_doc.get("status") == "completed":
                logger.info(f"ℹ️ Call {call_sid} already marked as completed, skipping update")
                return True  # Return True - call is in correct state
            
            now = datetime.utcnow().isoformat()
            
            # EDGE CASE 3: Calculate duration safely
            if duration_seconds is None:
                if call_doc.get("start_time"):
                    try:
                        start_time = datetime.fromisoformat(call_doc["start_time"])
                        end_time = datetime.fromisoformat(now)
                        calculated_duration = (end_time - start_time).total_seconds()
                        # EDGE CASE 4: Handle negative duration (clock skew or invalid data)
                        duration_seconds = max(0, calculated_duration)
                        if calculated_duration < 0:
                            logger.warning(f"⚠️ Negative duration calculated for {call_sid}: {calculated_duration}s, using 0")
                    except (ValueError, TypeError) as time_error:
                        logger.warning(f"⚠️ Could not parse start_time for {call_sid}: {time_error}, using duration 0")
                        duration_seconds = 0
                else:
                    duration_seconds = 0
                    logger.info(f"ℹ️ No start_time for call {call_sid}, using duration 0")
            
            # EDGE CASE 5: Update with proper error handling
            result = await collection.update_one(
                {"call_sid": call_sid, "status": {"$ne": "completed"}},  # Only update if not already completed
                {
                    "$set": {
                        "status": "completed",
                        "end_time": now,
                        "duration_seconds": duration_seconds,
                        "updated_at": now
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Ended call {call_sid}: duration {duration_seconds:.2f}s")
                return True
            else:
                # EDGE CASE 6: No modification - could be race condition or already completed
                # Check current status
                updated_doc = await collection.find_one({"call_sid": call_sid})
                if updated_doc and updated_doc.get("status") == "completed":
                    logger.info(f"ℹ️ Call {call_sid} was already completed (likely race condition)")
                    return True
                else:
                    logger.warning(f"⚠️ Call {call_sid} was not updated (matched count: {result.matched_count}, modified: {result.modified_count})")
                    return False  # Return False to trigger fallback in webhook handler
            
        except Exception as e:
            # EDGE CASE 7: Any unexpected error
            logger.error(f"Error ending call {call_sid}: {e}", exc_info=True)
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
                    # Map MongoDB status to UI status
                    # "active" -> "ongoing", everything else (completed, failed, etc.) -> "finished"
                    "status": "ongoing" if doc.get("status") == "active" else "finished",
                    "timestamp": doc.get("start_time"),
                    "duration": doc.get("duration_seconds"),
                    "conversation": conversation,
                    "callerNumber": doc.get("from_number"),  # Add for UI compatibility
                    "scheduled_call_id": doc.get("scheduled_call_id"),
                    "is_scheduled": doc.get("is_scheduled", False)
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
                "scheduled_call_id": doc.get("scheduled_call_id"),
                "is_scheduled": doc.get("is_scheduled", False)
            }
            
        except Exception as e:
            logger.error(f"Error getting call by sid: {e}")
            return None
    
    async def get_calls_for_user(
        self,
        user_phone_numbers: List[str],
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get calls filtered by user's phone numbers for multi-tenancy
        
        Args:
            user_phone_numbers: List of phone numbers owned by the user
            agent_id: Optional filter for specific phone number (must be in user_phone_numbers)
            status: Optional status filter
            limit: Max calls to return
        
        Returns:
            List of calls belonging to the user
        """
        if not is_mongodb_available():
            return []
        
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            
            # Build query - filter by user's phone numbers
            if agent_id:
                # Single phone number filter (already validated as belonging to user)
                query = {"agent_id": agent_id}
            else:
                # Filter by all user's phone numbers
                query = {"agent_id": {"$in": user_phone_numbers}}
            
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
                    "callerNumber": doc.get("from_number"),
                    "scheduled_call_id": doc.get("scheduled_call_id"),
                    "is_scheduled": doc.get("is_scheduled", False)
                })
            
            logger.info(f"✅ Retrieved {len(calls)} call(s) for user (filtered by {len(user_phone_numbers)} phone(s))")
            return calls
            
        except Exception as e:
            logger.error(f"Error getting calls for user: {e}")
            return []

