"""
Helper utilities for getting Twilio credentials from registered phones
"""

from typing import Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

async def get_twilio_credentials_for_phone(phone_number: str) -> Optional[Dict[str, str]]:
    """
    Get Twilio credentials for a phone number from registered phones.
    
    Args:
        phone_number: Phone number to get credentials for (e.g., "+15551234567")
    
    Returns:
        Dictionary with 'account_sid' and 'auth_token', or None if not found
    """
    try:
        from databases.mongodb_phone_store import MongoDBPhoneStore
        from databases.mongodb_db import is_mongodb_available
        
        if not is_mongodb_available():
            logger.debug("MongoDB not available, cannot get credentials from registered phones")
            return None
        
        phone_store = MongoDBPhoneStore()
        registered_phone = await phone_store.get_phone_by_number(phone_number)
        
        if registered_phone and registered_phone.get("isActive") != False:
            return {
                "account_sid": registered_phone.get("twilioAccountSid"),
                "auth_token": registered_phone.get("twilioAuthToken")
            }
        
        return None
    except Exception as e:
        logger.error(f"Error getting Twilio credentials for phone {phone_number}: {e}")
        return None

async def get_twilio_credentials_for_call(call_sid: str, to_number: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Get Twilio credentials for a call by looking up the phone number.
    
    Args:
        call_sid: Call SID (optional, for logging)
        to_number: Phone number that received the call (the "To" number)
    
    Returns:
        Dictionary with 'account_sid' and 'auth_token', or None if not found
    """
    if not to_number:
        # Try to get from call record in MongoDB
        try:
            from databases.mongodb_call_store import MongoDBCallStore
            from databases.mongodb_db import is_mongodb_available
            
            if is_mongodb_available():
                call_store = MongoDBCallStore()
                call = await call_store.get_call_by_sid(call_sid)
                if call:
                    to_number = call.get("to_number")
        except Exception as e:
            logger.warning(f"Could not get phone number from call record: {e}")
    
    if to_number:
        return await get_twilio_credentials_for_phone(to_number)
    
    return None

async def get_twilio_credentials(phone_number: Optional[str] = None, call_sid: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Get Twilio credentials from MongoDB only (registered phones).
    Credentials MUST be registered through the app UI - no fallback to .env.
    
    Args:
        phone_number: Phone number to get credentials for
        call_sid: Call SID (used to look up phone number if phone_number not provided)
    
    Returns:
        Dictionary with 'account_sid' and 'auth_token', or None if not found
    
    Raises:
        ValueError: If credentials are not found in MongoDB
    """
    # Try registered phones from MongoDB
    if phone_number:
        creds = await get_twilio_credentials_for_phone(phone_number)
        if creds:
            return creds
    
    if call_sid:
        creds = await get_twilio_credentials_for_call(call_sid, phone_number)
        if creds:
            return creds
    
    # No credentials found - must be registered through app UI
    logger.error(f"No Twilio credentials found in MongoDB for phone={phone_number}, call_sid={call_sid}. Please register the phone number through the app UI.")
    return None

