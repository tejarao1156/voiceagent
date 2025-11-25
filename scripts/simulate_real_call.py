import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from datetime import datetime
import uuid

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from databases.mongodb_call_store import MongoDBCallStore
from databases.mongodb_db import get_mongo_db, initialize_mongodb, test_connection

async def simulate_call():
    print("🚀 Simulating a real call flow...")
    
    # Initialize MongoDB
    if not initialize_mongodb():
        print("❌ Failed to initialize MongoDB")
        return
        
    if not await test_connection():
        print("❌ MongoDB connection test failed")
        return
    
    store = MongoDBCallStore()
    
    # 1. Create a new call
    call_sid = f"CA{uuid.uuid4().hex}"
    from_number = "+15550001111"
    to_number = "+18668134984"
    
    print(f"📞 Creating call {call_sid}...")
    success = await store.create_call(
        call_sid=call_sid,
        from_number=from_number,
        to_number=to_number
    )
    
    if success:
        print("✅ Call created successfully in MongoDB")
    else:
        print("❌ Failed to create call")
        return

    # 2. Add some transcript entries (simulating real-time conversation)
    transcript_lines = [
        ("assistant", "Hello! Thank you for calling DoDash AI. How can I help you today?"),
        ("user", "Hi, I'm interested in your premium plan."),
        ("assistant", "That's great! Our premium plan includes advanced voice analytics and unlimited agents. Would you like to hear more?"),
        ("user", "Yes, please tell me about the analytics."),
        ("assistant", "Certainly. You get real-time sentiment analysis, call transcription, and detailed reporting dashboards.")
    ]
    
    for role, text in transcript_lines:
        await asyncio.sleep(1) # Simulate delay
        print(f"📝 Adding transcript: {role}: {text[:20]}...")
        await store.update_call_transcript(call_sid, role, text)
    
    # 3. End the call
    await asyncio.sleep(1)
    print("End call...")
    await store.end_call(call_sid, duration_seconds=45.5)
    print("✅ Call flow simulation complete!")

if __name__ == "__main__":
    asyncio.run(simulate_call())
