"""
Webhook URL Generator
Generates unique webhook URLs for agents based on environment
"""
import logging
from typing import Dict, Optional
from config import TWILIO_WEBHOOK_BASE_URL

logger = logging.getLogger(__name__)

def generate_webhook_urls(
    agent_id: str,
    user_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate unique webhook URLs for an agent.
    
    Args:
        agent_id: MongoDB agent ID
        user_id: User/tenant ID (optional, defaults to "default" if not provided)
    
    Returns:
        Dictionary with incomingUrl and statusCallbackUrl
    """
    # Normalize webhook base URL (remove trailing slash)
    webhook_base = TWILIO_WEBHOOK_BASE_URL.rstrip('/')
    
    # Use user_id if provided, otherwise use "default"
    user_identifier = user_id if user_id else "default"
    
    # Generate URLs with user and agent identifiers
    incoming_url = f"{webhook_base}/webhooks/twilio/user/{user_identifier}/agent/{agent_id}/incoming"
    status_url = f"{webhook_base}/webhooks/twilio/user/{user_identifier}/agent/{agent_id}/status"
    
    logger.info(f"🔗 Generated webhook URLs for agent {agent_id}:")
    logger.info(f"   Incoming: {incoming_url}")
    logger.info(f"   Status: {status_url}")
    
    return {
        "incomingUrl": incoming_url,
        "statusCallbackUrl": status_url
    }

