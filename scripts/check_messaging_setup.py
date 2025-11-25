import asyncio
import logging
import sys
import os

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from databases.mongodb_phone_store import MongoDBPhoneStore
from databases.mongodb_message_agent_store import MongoDBMessageAgentStore
from databases.mongodb_db import initialize_mongodb

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def check_messaging_setup():
    print("\n🔍 Checking Messaging Agent Setup...\n")
    
    # Initialize MongoDB
    initialize_mongodb()
    
    phone_store = MongoDBPhoneStore()
    agent_store = MongoDBMessageAgentStore()
    
    # 1. List Registered Phone Numbers (All Types)
    print("📱 Registered Phone Numbers (All Types):")
    print("-" * 60)
    phones = await phone_store.list_phones(active_only=False)
    
    message_phones = {}
    if phones:
        for phone in phones:
            status = "✅ Active" if phone.get("isActive") else "❌ Inactive"
            p_type = phone.get("type", "calls")
            print(f"  • {phone.get('phoneNumber')} ({status})")
            print(f"    Type: {p_type}")
            print(f"    ID: {phone.get('id')}")
            if p_type == "messages":
                message_phones[phone.get('phoneNumber')] = phone
    else:
        print("  No phone numbers registered specifically for messages.")
    print("-" * 60)
    
    # 2. List Messaging Agents
    print("\n🤖 Messaging Agents:")
    print("-" * 60)
    agents = await agent_store.list_message_agents(active_only=False, include_deleted=False)
    
    if agents:
        for agent in agents:
            status = "✅ Active" if agent.get("active") else "❌ Inactive"
            phone = agent.get("phoneNumber")
            print(f"  • {agent.get('name')} ({status})")
            print(f"    ID: {agent.get('id')}")
            print(f"    Phone: {phone}")
            print(f"    Prompt: {agent.get('prompt')[:50]}..." if agent.get('prompt') else "    Prompt: N/A")
            
            # Check if phone exists in registered phones
            if phone in message_phones:
                print(f"    Linked Phone Status: ✅ Found in registered 'messages' phones")
            else:
                # Check if it exists as a 'calls' phone or not at all
                all_phones = await phone_store.list_phones(active_only=False)
                found_any = False
                for p in all_phones:
                    if p.get("phoneNumber") == phone:
                        found_any = True
                        p_type = p.get("type", "calls")
                        print(f"    Linked Phone Status: ⚠️ Found but type is '{p_type}' (expected 'messages')")
                        break
                if not found_any:
                    print(f"    Linked Phone Status: ❌ Phone number NOT registered in system")
            print("")
    else:
        print("  No messaging agents found.")
    print("-" * 60)

if __name__ == "__main__":
    asyncio.run(check_messaging_setup())
