"""
Scheduled Call Worker
Handles background processing of scheduled calls
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
from databases.mongodb_phone_store import MongoDBPhoneStore, normalize_phone_number
from utils.twilio_credentials import get_twilio_credentials_for_phone
from config import TWILIO_WEBHOOK_BASE_URL
from twilio.rest import Client

logger = logging.getLogger(__name__)

class ScheduledCallWorker:
    """Worker to process scheduled calls in the background"""
    
    def __init__(self):
        self.scheduled_call_store = MongoDBScheduledCallStore()
        self.phone_store = MongoDBPhoneStore()
        self.is_running = False
        self._task = None
        
    def start(self):
        """Start the worker task"""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("✅ Scheduled Call Worker started")
        
    def stop(self):
        """Stop the worker task"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            
    async def _worker_loop(self):
        """Main worker loop"""
        logger.info("🔄 Scheduled Call Worker loop running...")
        
        while self.is_running:
            try:
                # Check for pending calls
                await self._process_pending_calls()
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Scheduled Call Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Scheduled Call Worker loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Sleep even on error to avoid tight loop
                
    async def _process_pending_calls(self):
        """Process all pending calls scheduled for now or earlier"""
        try:
            # Get current time in ISO format
            now_iso = datetime.utcnow().isoformat()
            
            # Get pending calls
            pending_calls = await self.scheduled_call_store.get_pending_calls(before_datetime=now_iso)
            
            if not pending_calls:
                return
                
            logger.info(f"📞 Found {len(pending_calls)} pending scheduled calls to execute")
            
            for call in pending_calls:
                await self._execute_call(call)
                
        except Exception as e:
            logger.error(f"Error processing pending calls: {e}", exc_info=True)
            
    async def _execute_call(self, call_data: Dict[str, Any]):
        """Execute a single scheduled call with batch processing"""
        call_id = call_data.get("id")
        from_number_id = call_data.get("fromPhoneNumberId")
        to_numbers = call_data.get("toPhoneNumbers", [])
        call_type = call_data.get("callType")
        
        logger.info(f"🚀 Executing scheduled call {call_id} ({call_type}) from {from_number_id}")
        logger.info(f"   Targeting {len(to_numbers)} phone numbers")
        
        # Update status to in_progress (ongoing)
        await self.scheduled_call_store.update_scheduled_call(call_id, {
            "status": "in_progress",
            "started_at": datetime.utcnow().isoformat()
        })
        
        try:
            # Get from phone number details
            from_phone = None
            
            # 1. Try to get by ID first (most common case from UI)
            try:
                # This will return None if ID is invalid or not found
                from_phone = await self.phone_store.get_phone(from_number_id)
            except Exception as e:
                # Ignore errors here (like invalid ObjectId format), we'll try by number next
                pass

            # 2. If not found by ID, try by phone number string
            if not from_phone:
                try:
                    normalized_from = normalize_phone_number(from_number_id)
                    from_phone = await self.phone_store.get_phone_by_number(normalized_from, type_filter="calls")
                except:
                    logger.warning(f"Could not resolve from_number_id: {from_number_id} (neither ID nor Phone)")
                    from_phone = None

            if not from_phone:
                raise ValueError(f"Could not find registered phone for {from_number_id}")
                
            from_number = from_phone.get("phoneNumber")
            
            # Get Twilio credentials
            twilio_creds = await get_twilio_credentials_for_phone(from_number)
            if not twilio_creds:
                raise ValueError(f"No Twilio credentials found for {from_number}")
                
            client = Client(twilio_creds["account_sid"], twilio_creds["auth_token"])
            
            results = []
            BATCH_SIZE = 10
            
            # Process in batches
            for i in range(0, len(to_numbers), BATCH_SIZE):
                batch = to_numbers[i:i + BATCH_SIZE]
                logger.info(f"   Processing batch {i//BATCH_SIZE + 1}: {len(batch)} numbers")
                
                # Create tasks for this batch
                tasks = []
                for to_number in batch:
                    tasks.append(self._initiate_single_call(client, from_number, to_number, call_id))
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                
                # Small delay between batches to be nice to Twilio API
                if i + BATCH_SIZE < len(to_numbers):
                    await asyncio.sleep(1)
            
            # Update scheduled call status to completed
            await self.scheduled_call_store.update_scheduled_call(call_id, {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "results": results
            })
            logger.info(f"✅ Scheduled call {call_id} completed processing all numbers")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled call {call_id}: {e}")
            await self.scheduled_call_store.update_scheduled_call(call_id, {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })

    async def _initiate_single_call(self, client, from_number, to_number, scheduled_call_id):
        """Initiate a single call via Twilio"""
        try:
            normalized_to = normalize_phone_number(to_number)
            
            # Append scheduled call metadata to webhook URL
            webhook_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming?scheduled_call_id={scheduled_call_id}&is_scheduled=true"
            
            # Run blocking Twilio call in a thread
            loop = asyncio.get_event_loop()
            call = await loop.run_in_executor(
                None,
                lambda: client.calls.create(
                    to=normalized_to,
                    from_=from_number,
                    url=webhook_url,
                    method="POST",
                    status_callback=f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status",
                    status_callback_event=["initiated", "ringing", "answered", "completed"],
                    status_callback_method="POST"
                )
            )
            
            logger.info(f"      ✅ Initiated call to {normalized_to}: {call.sid}")
            
            # Log the call to MongoDB calllogs collection
            await self._log_call_to_mongodb(
                call_sid=call.sid,
                from_number=from_number,
                to_number=normalized_to,
                scheduled_call_id=scheduled_call_id,
                direction="outbound",
                status="initiated"
            )
            
            return {
                "to": normalized_to,
                "status": "initiated",
                "call_sid": call.sid
            }
            
        except Exception as e:
            logger.error(f"      ❌ Failed to call {to_number}: {e}")
            return {
                "to": to_number,
                "status": "failed",
                "error": str(e)
            }
    
    async def _log_call_to_mongodb(
        self,
        call_sid: str,
        from_number: str,
        to_number: str,
        scheduled_call_id: str,
        direction: str,
        status: str
    ):
        """Log the call to MongoDB calllogs collection"""
        try:
            from databases.mongodb_call_store import MongoDBCallStore
            
            call_store = MongoDBCallStore()
            
            # Create call log entry using the correct MongoDB interface
            # The create_call method expects: call_sid, from_number, to_number as positional args
            # and scheduled_call_id, is_scheduled as optional kwargs
            await call_store.create_call(
                call_sid=call_sid,
                from_number=from_number,
                to_number=to_number,
                scheduled_call_id=scheduled_call_id,
                is_scheduled=True
            )
            
            logger.info(f"      📝 Logged call {call_sid} to MongoDB calllogs")
            
        except Exception as e:
            logger.error(f"      ⚠️ Failed to log call {call_sid} to MongoDB: {e}", exc_info=True)

