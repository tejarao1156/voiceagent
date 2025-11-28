"""
Scheduled Call Processor - Background task to execute scheduled calls
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from twilio.rest import Client

logger = logging.getLogger(__name__)

class ScheduledCallProcessor:
    """Process and execute scheduled calls at their scheduled time."""
    
    def __init__(self):
        self.running = False
        self.check_interval = 30  # Check every 30 seconds
        self.task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the scheduled call processor background task."""
        if self.running:
            logger.warning("Scheduled call processor is already running")
            return
            
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("🕒 Scheduled call processor started (checking every {} seconds)".format(self.check_interval))
        
    async def stop(self):
        """Stop the scheduled call processor."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduled call processor stopped")
        
    async def _run(self):
        """Main processing loop."""
        while self.running:
            try:
                await self._process_pending_calls()
            except Exception as e:
                logger.error(f"Error in scheduled call processor: {e}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)
            
    async def _process_pending_calls(self):
        """Check for and process pending scheduled calls."""
        from databases.mongodb_scheduled_call_store import MongoDBScheduledCallStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            return
            
        try:
            scheduled_call_store = MongoDBScheduledCallStore()
            
            #Get all pending calls
            pending_calls = await scheduled_call_store.list_scheduled_calls(status="pending")
            
            if not pending_calls:
                return
                
            now = datetime.now(timezone.utc)
            
            for call in pending_calls:
                try:
                    # Parse scheduled time
                    scheduled_time_str = call.get("scheduledDateTime")
                    if not scheduled_time_str:
                        logger.warning(f"Call {call.get('id')} has no scheduledDateTime")
                        continue
                    
                    # Handle both ISO format and datetime objects
                    if isinstance(scheduled_time_str, str):
                        # Parse ISO format: "2025-11-27T21:50"
                        # Add timezone if not present
                        if '+' not in scheduled_time_str and 'Z' not in scheduled_time_str:
                            scheduled_time_str += 'Z'  # Assume UTC
                        scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
                    else:
                        scheduled_time = scheduled_time_str
                        
                    # Make sure scheduled_time is timezone-aware
                    if scheduled_time.tzinfo is None:
                        scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
                    
                    # Check if it's time to execute
                    if now >= scheduled_time:
                        logger.info(f"⏰ Executing scheduled call: {call.get('id')}")
                        await self._execute_call(call, scheduled_call_store)
                    else:
                        time_remaining = (scheduled_time - now).total_seconds()
                        logger.debug(f"Call {call.get('id')} scheduled in {time_remaining:.0f} seconds")
                        
                except Exception as e:
                    logger.error(f"Error processing call {call.get('id')}: {e}", exc_info=True)
                    # Mark as failed
                    try:
                        await scheduled_call_store.update_scheduled_call(
                            call.get("id"),
                            {
                                "status": "failed",
                                "errorMessage": f"Processing error: {str(e)}",
                                "executedAt": datetime.now(timezone.utc).isoformat()
                            }
                        )
                    except Exception as update_error:
                        logger.error(f"Failed to update call status: {update_error}")
                        
        except Exception as e:
            logger.error(f"Error fetching pending calls: {e}", exc_info=True)
            
    async def _execute_call(self, call_data: dict, scheduled_call_store):
        """Execute a single scheduled call."""
        call_id = call_data.get("id")
        
        try:
            # Mark as in_progress
            await scheduled_call_store.update_scheduled_call(
                call_id,
                {"status": "in_progress", "executedAt": datetime.now(timezone.utc).isoformat()}
            )
            
            # Get phone number and Twilio credentials
            from databases.mongodb_phone_store import MongoDBPhoneStore
            phone_store = MongoDBPhoneStore()
            
            from_phone_id = call_data.get("fromPhoneNumberId")
            if not from_phone_id:
                raise ValueError("No fromPhoneNumberId in scheduled call")
            
            # Get registered phone
            registered_phone = await phone_store.get_phone(from_phone_id)
            if not registered_phone:
                # Try as phone number directly
                from databases.mongodb_phone_store import normalize_phone_number
                normalized = normalize_phone_number(from_phone_id)
                registered_phone = await phone_store.get_phone_by_number(normalized, type_filter="calls")
                
            if not registered_phone:
                raise ValueError(f"Phone number {from_phone_id} not found or not registered")
                
            if not registered_phone.get("isActive") or registered_phone.get("isDeleted"):
                raise ValueError(f"Phone number is inactive or deleted")
            
            # Get Twilio credentials
            twilio_account_sid = registered_phone.get("twilioAccountSid")
            twilio_auth_token = registered_phone.get("twilioAuthToken")
            from_number = registered_phone.get("phoneNumber")
            
            if not twilio_account_sid or not twilio_auth_token:
                raise ValueError("Twilio credentials not found for phone number")
            
            # Get recipients
            to_numbers = call_data.get("toPhoneNumbers", [])
            if not to_numbers:
                raise ValueError("No recipient phone numbers")
            
            # Get configuration
            from config import TWILIO_WEBHOOK_BASE_URL
            webhook_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming"
            status_callback_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status"
            
            # Prepare context for AI calls
            call_type = call_data.get("callType", "ai")
            custom_context = None
            
            if call_type == "ai":
                prompt_id = call_data.get("promptId")
                if prompt_id:
                    # Get prompt content
                    from databases.mongodb_prompt_store import MongoDBPromptStore
                    prompt_store = MongoDBPromptStore()
                    prompt = await prompt_store.get_prompt(prompt_id)
                    if prompt:
                        custom_context = prompt.get("content")
            
            # Initialize Twilio client
            client = Client(twilio_account_sid, twilio_auth_token)
            
            # Make calls to all recipients
            call_sids = []
            errors = []
            
            for to_number in to_numbers:
                try:
                    logger.info(f"📞 Calling {to_number} from {from_number}")
                    
                    # Prepare status callback with metadata
                    status_callback_params = {
                        "from": from_number,
                        "to": to_number,
                        "scheduled_call_id": call_id,
                        "call_type": call_type
                    }
                    
                    if custom_context:
                        status_callback_params["custom_context"] = custom_context
                    
                    # Make the call
                    twilio_call = client.calls.create(
                        from_=from_number,
                        to=to_number,
                        url=webhook_url,
                        status_callback=status_callback_url,
                        status_callback_event=["initiated", "ringing", "answered", "completed"],
                        status_callback_method="POST"
                    )
                    
                    call_sids.append(twilio_call.sid)
                    logger.info(f"✅ Call initiated: {twilio_call.sid}")
                    
                    # Log the call to MongoDB
                    await self._log_call(
                        call_sid=twilio_call.sid,
                        from_number=from_number,
                        to_number=to_number,
                        scheduled_call_id=call_id,
                        call_type=call_type,
                        prompt_content=custom_context
                    )
                    
                except Exception as e:
                    error_msg = f"Failed to call {to_number}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Update scheduled call status
            if call_sids and not errors:
                # All calls succeeded
                await scheduled_call_store.update_scheduled_call(
                    call_id,
                    {
                        "status": "completed",
                        "callSids": call_sids,
                        "completedAt": datetime.now(timezone.utc).isoformat()
                    }
                )
                logger.info(f"✅ Scheduled call {call_id} completed successfully ({len(call_sids)} calls)")
            elif call_sids and errors:
                # Partial success
                await scheduled_call_store.update_scheduled_call(
                    call_id,
                    {
                        "status": "completed",
                        "callSids": call_sids,
                        "errorMessage": "; ".join(errors),
                        "completedAt": datetime.now(timezone.utc).isoformat()
                    }
                )
                logger.warning(f"⚠️ Scheduled call {call_id} partially completed ({len(call_sids)}/{len(to_numbers)} succeeded)")
            else:
                # All failed
                raise ValueError("; ".join(errors))
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Failed to execute scheduled call {call_id}: {error_msg}", exc_info=True)
            
            # Mark as failed
            try:
                await scheduled_call_store.update_scheduled_call(
                    call_id,
                    {
                        "status": "failed",
                        "errorMessage": error_msg,
                        "failedAt": datetime.now(timezone.utc).isoformat()
                    }
                )
            except Exception as update_error:
                logger.error(f"Failed to update call status to failed: {update_error}")
    
    async def _log_call(
        self,
        call_sid: str,
        from_number: str,
        to_number: str,
        scheduled_call_id: str,
        call_type: str,
        prompt_content: Optional[str] = None
    ):
        """Log the call to MongoDB calllogs collection."""
        try:
            from databases.mongodb_call_store import MongoDBCallStore
            
            call_store = MongoDBCallStore()
            
            # Create call log entry
            call_log = {
                "callSid": call_sid,
                "fromPhoneNumber": from_number,
                "toPhoneNumber": to_number,
                "direction": "outbound",
                "callType": call_type,
                "scheduledCallId": scheduled_call_id,
                "status": "initiated",
                "startTime": datetime.now(timezone.utc),
                "metadata": {
                    "source": "scheduled_call",
                    "promptContent": prompt_content
                }
            }
            
            await call_store.create_call(call_log)
            logger.info(f"📝 Call {call_sid} logged to MongoDB")
            
        except Exception as e:
            logger.error(f"Failed to log call {call_sid} to MongoDB: {e}", exc_info=True)


# Global instance
_processor: Optional[ScheduledCallProcessor] = None

async def start_scheduled_call_processor():
    """Start the global scheduled call processor."""
    global _processor
    if _processor is None:
        _processor = ScheduledCallProcessor()
    await _processor.start()
    
async def stop_scheduled_call_processor():
    """Stop the global scheduled call processor."""
    global _processor
    if _processor:
        await _processor.stop()
