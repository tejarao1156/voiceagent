"""
Authentication Utilities
JWT token generation, verification, and user context management
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import logging
from config import SECRET_KEY

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24  # Token valid for 24 hours

def generate_jwt_token(user_id: str, email: str) -> str:
    """
    Generate a JWT token for authenticated user
    
    Args:
        user_id: User's UUID
        email: User's email address
        
    Returns:
        JWT token string
    """
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expiration,
        "iat": datetime.utcnow(),  # Issued at
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.info(f"Generated JWT token for user: {email}")
    
    return token

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None

def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user_id from JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        user_id if token is valid, None otherwise
    """
    payload = verify_jwt_token(token)
    if payload:
        return payload.get("user_id")
    return None

def get_cookie_settings(secure: bool = True) -> Dict[str, Any]:
    """
    Get standardized cookie settings for JWT
    
    Args:
        secure: Whether to set secure flag (True for production)
        
    Returns:
        Dictionary of cookie settings
    """
    return {
        "key": "auth_token",
        "httponly": True,  # Prevent JavaScript access
        "samesite": "lax",  # CSRF protection
        "secure": secure,  # HTTPS only in production
        "max_age": JWT_EXPIRATION_HOURS * 3600,  # Expiration in seconds
    }
