#!/usr/bin/env python3
"""
Test script to add an inbound message to verify the UI displays it on the left
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from databases.mongodb_message_store import MongoDBMessageStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_test_inbound_message():
    """Add a test inbound message from a customer"""
    store = MongoDBMessageStore()
    
    # Add an inbound message (from customer to agent)
    # This simulates a customer sending "Hello, I want to order food"
    result = await store.create_message(
        message_sid="TEST_INBOUND_" + str(int(asyncio.get_event_loop().time())),
        from_number="+19379935869",  # Customer number
        to_number="+12242423142",     # Agent number
        body="Hello, I want to order food",
        agent_id="+12242423142",
        conversation_id="dd0c7cc1-10a1-43fb-8afd-13609878ff17"  # Use existing conversation
    )
    
    if result:
        logger.info("✅ Successfully added test inbound message!")
        logger.info("   From: +19379935869 (Customer)")
        logger.info("   To: +12242423142 (Agent)")
        logger.info("   Message: 'Hello, I want to order food'")
        logger.info("   Direction: inbound")
        logger.info("   Role: user")
        logger.info("\nRefresh the Messages page in your browser to see the customer message on the LEFT")
    else:
        logger.error("❌ Failed to add test inbound message")

if __name__ == "__main__":
    asyncio.run(add_test_inbound_message())
