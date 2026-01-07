"""
Campaign Worker
Handles background processing of campaign items (Voice, SMS, WhatsApp)
With scheduling support and sequential execution
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
from utils.twilio_credentials import get_twilio_credentials_for_phone
from config import TWILIO_WEBHOOK_BASE_URL
from twilio.rest import Client

logger = logging.getLogger(__name__)

# Configuration - Parallel batch processing
BATCH_SIZE = int(os.getenv("CAMPAIGN_BATCH_SIZE", "10"))  # Process 10 items concurrently
ITEM_DELAY_SECONDS = int(os.getenv("CAMPAIGN_ITEM_DELAY_SECONDS", "1"))  # Delay between batches


class CampaignWorker:
    """Worker to process campaigns in the background with scheduling support"""
    
    def __init__(self):
        self.campaign_store = MongoDBCampaignStore()
        self.phone_store = MongoDBPhoneStore()
        self.message_store = MongoDBMessageStore()
        self.execution_store = MongoDBCampaignExecutionStore()
        self.is_running = False
        self._task = None
    
    async def start(self):
        """Start the worker with crash recovery"""
        if self.is_running:
            return
        self.is_running = True
        
        # Crash recovery: Reset any stuck in_progress items from previous run
        await self._recover_from_crash()
        
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("✅ Campaign Worker started (parallel batch mode)")
    
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
                await asyncio.sleep(5)
                
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
        """Process a single campaign - send a BATCH of items in parallel"""
        campaign_id = campaign.get("id")
        campaign_name = campaign.get("name", "Untitled")
        campaign_type = campaign.get("type")
        config = campaign.get("config", {})
        user_id = campaign.get("userId")
        
        try:
            # Atomically acquire a batch of pending items (locks them)
            locked_items = await self.campaign_store.acquire_pending_items(campaign_id, BATCH_SIZE)
            
            if not locked_items:
                # No more pending items - mark campaign as completed
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
            
            # Process all items in parallel using asyncio.gather
            logger.info(f"📤 Processing batch of {len(locked_items)} items for {campaign_name}...")
            
            tasks = []
            for item in locked_items:
                if campaign_type == "voice":
                    tasks.append(self._send_voice(client, from_number, item, config, context))
                elif campaign_type == "sms":
                    tasks.append(self._send_sms(client, from_number, item, config, context))
                elif campaign_type == "whatsapp":
                    tasks.append(self._send_whatsapp(client, from_number, item, config, context))
            
            # Execute all tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update campaign stats
            await self.campaign_store.update_campaign_stats(campaign_id)
            
            # Delay before next batch
            logger.info(f"   Waiting {ITEM_DELAY_SECONDS}s before next batch...")
            await asyncio.sleep(ITEM_DELAY_SECONDS)
            
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


# Singleton instance
_campaign_worker: Optional[CampaignWorker] = None


def get_campaign_worker() -> CampaignWorker:
    """Get or create the campaign worker singleton"""
    global _campaign_worker
    if _campaign_worker is None:
        _campaign_worker = CampaignWorker()
    return _campaign_worker
