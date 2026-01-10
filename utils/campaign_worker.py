"""
Campaign Worker
Handles background processing of campaign items (Voice, SMS, WhatsApp)
With scheduling support, type-specific concurrency limits, and completion waiting
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from databases.mongodb_campaign_store import MongoDBCampaignStore
from databases.mongodb_phone_store import MongoDBPhoneStore, normalize_phone_number
from databases.mongodb_message_store import MongoDBMessageStore
from databases.mongodb_campaign_execution_store import MongoDBCampaignExecutionStore
from databases.mongodb_campaign_queue_store import MongoDBCampaignQueueStore
from databases.mongodb_campaign_pending_store import MongoDBCampaignPendingStore
from utils.twilio_credentials import get_twilio_credentials_for_phone
from config import (
    TWILIO_WEBHOOK_BASE_URL,
    CAMPAIGN_VOICE_WORKERS, CAMPAIGN_VOICE_BATCH_SIZE,
    CAMPAIGN_MESSAGE_WORKERS, CAMPAIGN_MESSAGE_BATCH_SIZE,
    CAMPAIGN_POLL_INTERVAL,
    CAMPAIGN_VOICE_BATCH_DELAY, CAMPAIGN_MESSAGE_BATCH_DELAY,
    CAMPAIGN_VOICE_TIMEOUT
)
from twilio.rest import Client

logger = logging.getLogger(__name__)


class CampaignWorker:
    """Worker to process campaigns in the background with type-specific concurrency limits"""
    
    def __init__(self):
        self.campaign_store = MongoDBCampaignStore()
        self.phone_store = MongoDBPhoneStore()
        self.message_store = MongoDBMessageStore()
        self.execution_store = MongoDBCampaignExecutionStore()
        self.queue_store = MongoDBCampaignQueueStore()
        self.pending_store = MongoDBCampaignPendingStore()  # Track pending voice calls
        self.is_running = False
        self._task = None
        
        # Type-specific semaphores for concurrency control
        # Voice: heavy (streaming, memory) - limit concurrency
        # Message (SMS/WhatsApp): lightweight - share same semaphore
        self._voice_semaphore = asyncio.Semaphore(CAMPAIGN_VOICE_WORKERS)
        self._message_semaphore = asyncio.Semaphore(CAMPAIGN_MESSAGE_WORKERS)
    
    def _get_type_config(self, campaign_type: str) -> Dict[str, Any]:
        """Get batch size, semaphore, and delay for campaign type"""
        configs = {
            "voice": {
                "batch_size": CAMPAIGN_VOICE_BATCH_SIZE,
                "semaphore": self._voice_semaphore,
                "workers": CAMPAIGN_VOICE_WORKERS,
                "name": "Voice",
                "delay": CAMPAIGN_VOICE_BATCH_DELAY,
                "wait_for_completion": True  # Voice waits for webhook
            },
            "sms": {
                "batch_size": CAMPAIGN_MESSAGE_BATCH_SIZE,
                "semaphore": self._message_semaphore,
                "workers": CAMPAIGN_MESSAGE_WORKERS,
                "name": "SMS",
                "delay": CAMPAIGN_MESSAGE_BATCH_DELAY,
                "wait_for_completion": False  # SMS just uses delay
            },
            "whatsapp": {
                "batch_size": CAMPAIGN_MESSAGE_BATCH_SIZE,
                "semaphore": self._message_semaphore,
                "workers": CAMPAIGN_MESSAGE_WORKERS,
                "name": "WhatsApp",
                "delay": CAMPAIGN_MESSAGE_BATCH_DELAY,
                "wait_for_completion": False  # WhatsApp just uses delay
            }
        }
        return configs.get(campaign_type, configs["sms"])
    
    async def start(self):
        """Start the worker with crash recovery"""
        if self.is_running:
            return
        self.is_running = True
        
        # Crash recovery: Reset any stuck in_progress items from previous run
        await self._recover_from_crash()
        
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("✅ Campaign Worker started with type-specific concurrency:")
        logger.info(f"   📞 Voice:   {CAMPAIGN_VOICE_WORKERS} workers, batch {CAMPAIGN_VOICE_BATCH_SIZE}, waits for completion (timeout {CAMPAIGN_VOICE_TIMEOUT}s)")
        logger.info(f"   📱 Message: {CAMPAIGN_MESSAGE_WORKERS} workers, batch {CAMPAIGN_MESSAGE_BATCH_SIZE}, {CAMPAIGN_MESSAGE_BATCH_DELAY}s delay after batch (SMS + WhatsApp)")
    
    
    async def _recover_from_crash(self):
        """Reset in_progress items for all running campaigns (crash recovery)"""
        try:
            running_campaigns = await self.campaign_store.list_campaigns(status="running")
            for campaign in running_campaigns:
                reset_count = await self.campaign_store.reset_in_progress_items(campaign["id"])
                if reset_count > 0:
                    logger.info(f"🔄 Recovered {reset_count} stuck items for campaign {campaign['id']}")
        except Exception as e:
            logger.error(f"Error during crash recovery: {e}", exc_info=True)
    
    def stop(self):
        """Stop the worker"""
        self.is_running = False
        if self._task:
            self._task.cancel()
    
    async def _worker_loop(self):
        """Main worker loop - checks for scheduled and running campaigns"""
        logger.info("🔄 Campaign Worker loop running...")
        
        while self.is_running:
            try:
                # 1. Check for scheduled campaigns that are ready to run
                await self._check_scheduled_campaigns()
                
                # 2. Process running campaigns
                running_campaigns = await self.campaign_store.list_campaigns(status="running")
                
                for campaign in running_campaigns:
                    # Check if campaign is still running (might have been paused)
                    current = await self.campaign_store.get_campaign(campaign["id"])
                    if current and current.get("status") == "running":
                        await self._process_campaign(current)
                
                # Sleep before next check
                await asyncio.sleep(CAMPAIGN_POLL_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Campaign Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Campaign Worker: {e}", exc_info=True)
                await asyncio.sleep(10)
    
    async def _check_scheduled_campaigns(self):
        """Check for scheduled campaigns ready to run and start them"""
        try:
            ready_campaigns = await self.campaign_store.get_ready_scheduled_campaigns()
            
            for campaign in ready_campaigns:
                campaign_id = campaign["id"]
                logger.info(f"📅 Starting scheduled campaign: {campaign_id} - {campaign.get('name')}")
                
                # Reset any in_progress items (crash recovery)
                await self.campaign_store.reset_in_progress_items(campaign_id)
                
                # Move to running
                await self.campaign_store.update_campaign(campaign_id, {"status": "running"})
                
        except Exception as e:
            logger.error(f"Error checking scheduled campaigns: {e}", exc_info=True)
    
    async def _process_campaign(self, campaign: Dict[str, Any]):
        """Process a single campaign with type-specific concurrency limits"""
        campaign_id = campaign.get("id")
        campaign_name = campaign.get("name", "Untitled")
        campaign_type = campaign.get("type")
        config = campaign.get("config", {})
        user_id = campaign.get("userId")
        
        # Get type-specific configuration
        type_config = self._get_type_config(campaign_type)
        batch_size = type_config["batch_size"]
        semaphore = type_config["semaphore"]
        type_name = type_config["name"]
        max_workers = type_config["workers"]
        
        try:
            # Acquire batch of phones using type-specific batch size
            phone_batch = await self.queue_store.acquire_batch(campaign_id, batch_size)
            
            if not phone_batch:
                # No more phones - mark campaign as completed
                await self.campaign_store.update_campaign(campaign_id, {
                    "status": "completed",
                    "progress_percent": 100.0
                })
                logger.info(f"✅ Campaign {campaign_id} ({campaign_name}) completed")
                return
            
            # Get from number and credentials
            from_number = config.get("fromNumber")
            if not from_number:
                logger.error(f"Campaign {campaign_id} missing fromNumber")
                await self.campaign_store.update_campaign(campaign_id, {"status": "failed"})
                return
            
            twilio_creds = await get_twilio_credentials_for_phone(from_number)
            if not twilio_creds:
                logger.error(f"No Twilio credentials for {from_number}")
                await self.campaign_store.update_campaign(campaign_id, {"status": "failed"})
                return
            
            client = Client(twilio_creds["account_sid"], twilio_creds["auth_token"])
            
            # Create context for logging
            context = {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "user_id": user_id
            }
            
            # Log batch processing with type info
            logger.info(f"📤 [{type_name}] Processing {len(phone_batch)} phones for '{campaign_name}' (max {max_workers} concurrent)")
            
            success_phones = []
            failed_phones = []
            call_sids = []  # Track call SIDs for voice completion waiting
            
            async def process_phone_with_semaphore(phone: str):
                """Process a single phone with semaphore-limited concurrency"""
                async with semaphore:
                    try:
                        if campaign_type == "voice":
                            # For voice, get call_sid for completion tracking
                            result = await self._send_voice_simple(client, from_number, phone, config, context)
                            if result:  # result is call_sid or None
                                call_sids.append(result)
                                success_phones.append(phone)
                            else:
                                failed_phones.append(phone)
                        elif campaign_type == "sms":
                            result = await self._send_sms_simple(client, from_number, phone, config, context)
                            if result:
                                success_phones.append(phone)
                            else:
                                failed_phones.append(phone)
                        elif campaign_type == "whatsapp":
                            result = await self._send_whatsapp_simple(client, from_number, phone, config, context)
                            if result:
                                success_phones.append(phone)
                            else:
                                failed_phones.append(phone)
                        else:
                            failed_phones.append(phone)
                    except Exception as e:
                        logger.error(f"Error processing {phone}: {e}")
                        failed_phones.append(phone)
            
            # Execute all with semaphore-limited concurrency
            await asyncio.gather(
                *[process_phone_with_semaphore(p) for p in phone_batch],
                return_exceptions=True
            )
            
            # Wait for completion based on type
            batch_delay = type_config["delay"]
            wait_for_completion = type_config["wait_for_completion"]
            
            if wait_for_completion and call_sids:
                # Voice: Wait for all calls to complete via webhook
                logger.info(f"   ⏳ [{type_name}] Waiting for {len(call_sids)} calls to complete...")
                completion_stats = await self.pending_store.wait_for_completion(
                    campaign_id, 
                    timeout_seconds=CAMPAIGN_VOICE_TIMEOUT
                )
                logger.info(f"   ✅ [{type_name}] Calls completed: {completion_stats}")
                # Clear pending items for this batch
                await self.pending_store.clear_campaign_pending(campaign_id)
            else:
                # SMS/WhatsApp: Simple delay
                logger.info(f"   ✅ [{type_name}] Batch sent: {len(success_phones)} success, {len(failed_phones)} failed. Waiting {batch_delay}s...")
                await asyncio.sleep(batch_delay)
            
            # Record batch results
            await self.queue_store.record_batch_results(campaign_id, success_phones, failed_phones)
            
            # Update campaign stats
            results = await self.queue_store.get_results(campaign_id)
            if results:
                total = results.get("total", 1)
                processed = results.get("processed", 0)
                progress = (processed / total) * 100 if total > 0 else 0
                await self.campaign_store.update_campaign(campaign_id, {
                    "progress_percent": progress,
                    "stats": {
                        "total": total,
                        "pending": total - processed,
                        "sent": results.get("success_count", 0),
                        "failed": results.get("failed_count", 0)
                    }
                })
            
        except Exception as e:
            logger.error(f"Error processing campaign {campaign_id}: {e}", exc_info=True)
    
    async def _send_voice(self, client: Client, from_number: str, item: Dict, config: Dict, context: Dict):
        """Initiate a voice call"""
        item_id = item.get("id")
        to_number = normalize_phone_number(item.get("phone_number", ""))
        campaign_id = context.get("campaign_id")
        campaign_name = context.get("campaign_name")
        user_id = context.get("user_id")
        
        try:
            # Include campaign info in webhook URL for call tracking
            webhook_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming?campaign_item_id={item_id}&campaign_id={campaign_id}"
            
            loop = asyncio.get_event_loop()
            call = await loop.run_in_executor(
                None,
                lambda: client.calls.create(
                    to=to_number,
                    from_=from_number,
                    url=webhook_url,
                    method="POST",
                    status_callback=f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status",
                    status_callback_event=["initiated", "ringing", "answered", "completed"],
                    status_callback_method="POST",
                    machine_detection="DetectMessageEnd",
                    machine_detection_timeout=30,
                    async_amd=True,
                    async_amd_status_callback=f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/amd-status",
                    async_amd_status_callback_method="POST"
                )
            )
            
            await self.campaign_store.update_item_status(item_id, "sent", call.sid)
            logger.info(f"      ✅ Call initiated to {to_number}: {call.sid}")
            
            # Log to campaign_executions
            await self.execution_store.log_execution(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                exec_type="voice",
                from_number=from_number,
                to_number=to_number,
                status="called",
                call_sid=call.sid,
                user_id=user_id
            )
            
        except Exception as e:
            await self.campaign_store.update_item_status(item_id, "failed", str(e))
            logger.error(f"      ❌ Failed to call {to_number}: {e}")
            
            # Log failure to campaign_executions
            await self.execution_store.log_execution(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                exec_type="voice",
                from_number=from_number,
                to_number=to_number,
                status="failed",
                error=str(e),
                user_id=user_id
            )
    
    async def _send_sms(self, client: Client, from_number: str, item: Dict, config: Dict, context: Dict):
        """Send an SMS message"""
        item_id = item.get("id")
        to_number = normalize_phone_number(item.get("phone_number", ""))
        message_body = config.get("messageBody", "")
        campaign_id = context.get("campaign_id")
        campaign_name = context.get("campaign_name")
        user_id = context.get("user_id")
        
        try:
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    to=to_number,
                    from_=from_number,
                    body=message_body
                )
            )
            
            await self.campaign_store.update_item_status(item_id, "sent", message.sid)
            logger.info(f"      ✅ SMS sent to {to_number}: {message.sid}")

            # Store in conversation history with campaign link
            await self.message_store.create_outbound_message(
                message_sid=message.sid,
                from_number=from_number,
                to_number=to_number,
                body=message_body,
                channel="sms",
                campaign_id=campaign_id
            )
            
            # Log to campaign_executions
            await self.execution_store.log_execution(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                exec_type="sms",
                from_number=from_number,
                to_number=to_number,
                status="sent",
                message_sid=message.sid,
                user_id=user_id
            )
            
        except Exception as e:
            await self.campaign_store.update_item_status(item_id, "failed", str(e))
            logger.error(f"      ❌ Failed SMS to {to_number}: {e}")
            
            # Log failure to campaign_executions
            await self.execution_store.log_execution(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                exec_type="sms",
                from_number=from_number,
                to_number=to_number,
                status="failed",
                error=str(e),
                user_id=user_id
            )
    
    async def _send_whatsapp(self, client: Client, from_number: str, item: Dict, config: Dict, context: Dict):
        """Send a WhatsApp message"""
        item_id = item.get("id")
        to_number = normalize_phone_number(item.get("phone_number", ""))
        message_body = config.get("messageBody", "")
        campaign_id = context.get("campaign_id")
        campaign_name = context.get("campaign_name")
        user_id = context.get("user_id")
        
        # WhatsApp requires whatsapp: prefix
        whatsapp_from = f"whatsapp:{from_number}"
        whatsapp_to = f"whatsapp:{to_number}"
        
        try:
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    to=whatsapp_to,
                    from_=whatsapp_from,
                    body=message_body
                )
            )
            
            await self.campaign_store.update_item_status(item_id, "sent", message.sid)
            logger.info(f"      ✅ WhatsApp sent to {to_number}: {message.sid}")

            # Store in conversation history with campaign link
            await self.message_store.create_outbound_message(
                message_sid=message.sid,
                from_number=from_number,
                to_number=to_number,
                body=message_body,
                channel="whatsapp",
                campaign_id=campaign_id
            )
            
            # Log to campaign_executions
            await self.execution_store.log_execution(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                exec_type="whatsapp",
                from_number=from_number,
                to_number=to_number,
                status="sent",
                message_sid=message.sid,
                user_id=user_id
            )
            
        except Exception as e:
            await self.campaign_store.update_item_status(item_id, "failed", str(e))
            logger.error(f"      ❌ Failed WhatsApp to {to_number}: {e}")
            
            # Log failure to campaign_executions
            await self.execution_store.log_execution(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                exec_type="whatsapp",
                from_number=from_number,
                to_number=to_number,
                status="failed",
                error=str(e),
                user_id=user_id
            )
    
    # ==================== SIMPLIFIED METHODS FOR QUEUE SYSTEM ====================
    
    async def _send_voice_simple(self, client: Client, from_number: str, phone: str, config: Dict, context: Dict) -> Optional[str]:
        """Simplified voice call - returns call_sid on success, None on failure
        
        Creates a pending item for completion tracking via webhook.
        """
        to_number = normalize_phone_number(phone)
        campaign_id = context.get("campaign_id")
        campaign_name = context.get("campaign_name")
        user_id = context.get("user_id")
        
        try:
            webhook_url = f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/incoming?campaign_id={campaign_id}"
            
            loop = asyncio.get_event_loop()
            call = await loop.run_in_executor(
                None,
                lambda: client.calls.create(
                    to=to_number,
                    from_=from_number,
                    url=webhook_url,
                    method="POST",
                    status_callback=f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/status",
                    status_callback_event=["initiated", "ringing", "answered", "completed"],
                    status_callback_method="POST",
                    machine_detection="DetectMessageEnd",
                    machine_detection_timeout=30,
                    async_amd=True,
                    async_amd_status_callback=f"{TWILIO_WEBHOOK_BASE_URL}/webhooks/twilio/amd-status",
                    async_amd_status_callback_method="POST"
                )
            )
            
            logger.info(f"      ✅ Call initiated to {to_number}: {call.sid}")
            
            # Create pending item for completion tracking
            await self.pending_store.create_pending(
                campaign_id=campaign_id,
                phone=phone,
                item_type="voice",
                sid=call.sid
            )
            
            await self.execution_store.log_execution(
                campaign_id=campaign_id, campaign_name=campaign_name, exec_type="voice",
                from_number=from_number, to_number=to_number, status="called",
                call_sid=call.sid, user_id=user_id
            )
            return call.sid  # Return call_sid for tracking
            
        except Exception as e:
            logger.error(f"      ❌ Failed call to {to_number}: {e}")
            await self.execution_store.log_execution(
                campaign_id=campaign_id, campaign_name=campaign_name, exec_type="voice",
                from_number=from_number, to_number=to_number, status="failed",
                error=str(e), user_id=user_id
            )
            return None
    
    async def _send_sms_simple(self, client: Client, from_number: str, phone: str, config: Dict, context: Dict) -> bool:
        """Simplified SMS send - returns True on success, False on failure"""
        to_number = normalize_phone_number(phone)
        message_body = config.get("messageBody", "")
        campaign_id = context.get("campaign_id")
        campaign_name = context.get("campaign_name")
        user_id = context.get("user_id")
        
        try:
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: client.messages.create(to=to_number, from_=from_number, body=message_body)
            )
            
            logger.info(f"      ✅ SMS sent to {to_number}: {message.sid}")
            await self.message_store.create_outbound_message(
                message_sid=message.sid, from_number=from_number, to_number=to_number,
                body=message_body, channel="sms", campaign_id=campaign_id
            )
            await self.execution_store.log_execution(
                campaign_id=campaign_id, campaign_name=campaign_name, exec_type="sms",
                from_number=from_number, to_number=to_number, status="sent",
                message_sid=message.sid, user_id=user_id
            )
            return True
            
        except Exception as e:
            logger.error(f"      ❌ Failed SMS to {to_number}: {e}")
            await self.execution_store.log_execution(
                campaign_id=campaign_id, campaign_name=campaign_name, exec_type="sms",
                from_number=from_number, to_number=to_number, status="failed",
                error=str(e), user_id=user_id
            )
            return False
    
    async def _send_whatsapp_simple(self, client: Client, from_number: str, phone: str, config: Dict, context: Dict) -> bool:
        """Simplified WhatsApp send - returns True on success, False on failure"""
        to_number = normalize_phone_number(phone)
        message_body = config.get("messageBody", "")
        campaign_id = context.get("campaign_id")
        campaign_name = context.get("campaign_name")
        user_id = context.get("user_id")
        
        whatsapp_from = f"whatsapp:{from_number}"
        whatsapp_to = f"whatsapp:{to_number}"
        
        try:
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: client.messages.create(to=whatsapp_to, from_=whatsapp_from, body=message_body)
            )
            
            logger.info(f"      ✅ WhatsApp sent to {to_number}: {message.sid}")
            await self.message_store.create_outbound_message(
                message_sid=message.sid, from_number=from_number, to_number=to_number,
                body=message_body, channel="whatsapp", campaign_id=campaign_id
            )
            await self.execution_store.log_execution(
                campaign_id=campaign_id, campaign_name=campaign_name, exec_type="whatsapp",
                from_number=from_number, to_number=to_number, status="sent",
                message_sid=message.sid, user_id=user_id
            )
            return True
            
        except Exception as e:
            logger.error(f"      ❌ Failed WhatsApp to {to_number}: {e}")
            await self.execution_store.log_execution(
                campaign_id=campaign_id, campaign_name=campaign_name, exec_type="whatsapp",
                from_number=from_number, to_number=to_number, status="failed",
                error=str(e), user_id=user_id
            )
            return False


# Singleton instance
_campaign_worker: Optional[CampaignWorker] = None


def get_campaign_worker() -> CampaignWorker:
    """Get or create the campaign worker singleton"""
    global _campaign_worker
    if _campaign_worker is None:
        _campaign_worker = CampaignWorker()
    return _campaign_worker
