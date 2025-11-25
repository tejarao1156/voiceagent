import asyncio
import sys
import os

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from databases.mongodb_phone_store import MongoDBPhoneStore
from databases.mongodb_db import initialize_mongodb

async def check_deleted_phone():
    initialize_mongodb()
    phone_store = MongoDBPhoneStore()
    
    # Get the phone we just deleted (including deleted ones)
    from databases.mongodb_db import get_mongo_db
    db = get_mongo_db()
    collection = db["registered_phone_numbers"]
    
    phone = await collection.find_one({"_id": __import__('bson').ObjectId("6924a9129eb61555b4484dc7")})
    
    if phone:
        print(f"\n📱 Phone: {phone.get('phoneNumber')}")
        print(f"   Type: {phone.get('type')}")
        print(f"   isDeleted: {phone.get('isDeleted')}")
        print(f"   isActive: {phone.get('isActive')}")
        
        if phone.get('isDeleted'):
            print("\n✅ Phone is correctly marked as DELETED in MongoDB")
        else:
            print("\n❌ Phone is NOT marked as deleted")
    else:
        print("❌ Phone not found in database")
    
    # Check if it appears in the API list
    phones = await phone_store.list_phones(active_only=False, type_filter="messages")
    print(f"\n📋 Messaging Phones in API (filtered):")
    for p in phones:
        print(f"   • {p.get('phoneNumber')} (isDeleted: {p.get('isDeleted', False)})")
    
    if not any(p.get('id') == '6924a9129eb61555b4484dc7' for p in phones):
        print("\n✅ Deleted phone is correctly HIDDEN from API list")
    else:
        print("\n❌ Deleted phone is still showing in API list")

if __name__ == "__main__":
    asyncio.run(check_deleted_phone())
