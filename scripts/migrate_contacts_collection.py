"""
Migration Script: Rename 'contacts' collection to 'campaign_contacts'

Run this script once to migrate existing data after updating the code.
Safe to run multiple times - only migrates if old collection exists.

Usage:
    python scripts/migrate_contacts_collection.py
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from databases.mongodb_db import initialize_mongodb, get_mongo_db, is_mongodb_available, test_connection


async def migrate():
    """Rename 'contacts' collection to 'campaign_contacts'"""
    
    # Initialize MongoDB connection
    print("🔌 Initializing MongoDB connection...")
    init_result = initialize_mongodb()
    if not init_result:
        print("❌ Failed to initialize MongoDB. Check MONGODB_URL in .env")
        return False
    
    # Test the connection
    test_result = await test_connection()
    if not test_result:
        print("❌ MongoDB connection test failed.")
        return False
    
    print("✅ MongoDB connected successfully!")
    
    db = get_mongo_db()
    if db is None:
        print("❌ Could not get MongoDB database instance.")
        return False
    
    old_name = "contacts"
    new_name = "campaign_contacts"
    
    # Check if old collection exists
    collections = await db.list_collection_names()
    print(f"📋 Found collections: {collections}")
    
    if old_name not in collections:
        if new_name in collections:
            print(f"✅ Collection '{new_name}' already exists. No migration needed.")
            return True
        else:
            print(f"ℹ️ Neither '{old_name}' nor '{new_name}' collection exists. Fresh start.")
            return True
    
    if new_name in collections:
        print(f"⚠️ Both '{old_name}' and '{new_name}' exist! Manual intervention required.")
        print(f"   Check if data needs to be merged or if one should be deleted.")
        return False
    
    # Count documents
    old_count = await db[old_name].count_documents({})
    print(f"📊 Found {old_count} documents in '{old_name}' collection.")
    
    # Rename collection
    try:
        await db[old_name].rename(new_name)
        print(f"✅ Successfully renamed '{old_name}' to '{new_name}'!")
        
        # Verify
        new_count = await db[new_name].count_documents({})
        print(f"✅ Verified: {new_count} documents in '{new_name}' collection.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error renaming collection: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Campaign Contacts Migration Script")
    print("=" * 50)
    print()
    
    result = asyncio.run(migrate())
    
    print()
    if result:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed. See errors above.")
    
    sys.exit(0 if result else 1)
