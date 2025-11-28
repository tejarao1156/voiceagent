"""
MongoDB User Store for Authentication
Handles user registration, login, and user management
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import logging
import bcrypt
from databases.mongodb_db import get_mongo_db, is_mongodb_available

logger = logging.getLogger(__name__)

class MongoDBUserStore:
    """MongoDB store for user authentication and management"""
    
    def __init__(self):
        self.collection_name = "users"
    
    def _get_collection(self):
        """Get the users collection from MongoDB"""
        db = get_mongo_db()
        if db is None:
            raise Exception("MongoDB is not available")
        return db[self.collection_name]
    
    async def create_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Create a new user with email and password
        
        Args:
            email: User's email address (unique identifier)
            password: Plain text password (will be hashed)
            
        Returns:
            User document with user_id, email, created_at
            
        Raises:
            Exception: If email already exists or MongoDB unavailable
        """
        if not is_mongodb_available():
            raise Exception("MongoDB is not available")
        
        # Normalize email
        email = email.lower().strip()
        
        # Check if user already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise Exception("User with this email already exists")
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Generate UUID for user
        user_id = str(uuid.uuid4())
        
        # Create user document
        user_doc = {
            "user_id": user_id,
            "email": email,
            "password_hash": password_hash.decode('utf-8'),
            "isActive": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Insert into MongoDB
        collection = self._get_collection()
        await collection.insert_one(user_doc)
        
        logger.info(f"Created new user: {email} with user_id: {user_id}")
        
        # Return user without password_hash
        return {
            "user_id": user_id,
            "email": email,
            "isActive": True,
            "created_at": user_doc["created_at"],
        }
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email address
        
        Args:
            email: User's email address
            
        Returns:
            User document or None if not found
        """
        if not is_mongodb_available():
            return None
        
        email = email.lower().strip()
        collection = self._get_collection()
        user = await collection.find_one({"email": email})
        
        if user:
            # Remove MongoDB _id field
            user.pop('_id', None)
        
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by user_id
        
        Args:
            user_id: User's UUID
            
        Returns:
            User document or None if not found
        """
        if not is_mongodb_available():
            return None
        
        collection = self._get_collection()
        user = await collection.find_one({"user_id": user_id})
        
        if user:
            # Remove MongoDB _id field
            user.pop('_id', None)
        
        return user
    
    async def verify_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify user password and return user if valid
        
        Args:
            email: User's email address
            password: Plain text password to verify
            
        Returns:
            User document (without password_hash) if password is valid, None otherwise
        """
        user = await self.get_user_by_email(email)
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {email}")
            return None
        
        # Check if password matches
        password_hash = user.get("password_hash", "")
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            logger.info(f"Successful login for user: {email}")
            # Return user without password_hash
            return {
                "user_id": user["user_id"],
                "email": user["email"],
                "isActive": user.get("isActive", True),
                "created_at": user.get("created_at"),
            }
        else:
            logger.warning(f"Invalid password for user: {email}")
            return None
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update user information
        
        Args:
            user_id: User's UUID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not is_mongodb_available():
            return False
        
        # Don't allow updating user_id or password_hash directly
        updates.pop('user_id', None)
        updates.pop('password_hash', None)
        
        # Add updated_at timestamp
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        collection = self._get_collection()
        result = await collection.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def update_password(self, user_id: str, new_password: str) -> bool:
        """
        Update user password
        
        Args:
            user_id: User's UUID
            new_password: New plain text password (will be hashed)
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not is_mongodb_available():
            return False
        
        # Hash new password
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        collection = self._get_collection()
        result = await collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "password_hash": password_hash.decode('utf-8'),
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        
        return result.modified_count > 0
    
    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user account
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if deactivated successfully, False otherwise
        """
        return await self.update_user(user_id, {"isActive": False})
    
    async def activate_user(self, user_id: str) -> bool:
        """
        Activate a user account
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if activated successfully, False otherwise
        """
        return await self.update_user(user_id, {"isActive": True})
