"""
Check Agents for Phone Number
"""
import asyncio
import logging
from databases.mongodb_db import initialize_mongodb
from databases.mongodb_agent_store import MongoDBAgentStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_agents():
    initialize_mongodb()
    store = MongoDBAgentStore()
    
    phone_number = "+15551234567"
    normalized_target = phone_number.replace("+1", "").replace("+", "").replace("-", "").replace(" ", "")
    
    print(f"\n🔍 Checking agents for phone: {phone_number} (Normalized: {normalized_target})")
    
    agents = await store.list_agents(active_only=False)
    print(f"📋 Total agents found: {len(agents)}")
    
    found = False
    for agent in agents:
        agent_phone = agent.get("phoneNumber", "")
        normalized_agent_phone = agent_phone.replace("+1", "").replace("+", "").replace("-", "").replace(" ", "")
        
        print(f"\n   Agent: {agent.get('name')}")
        print(f"   ID: {agent.get('id')}")
        print(f"   Phone: {agent_phone} (Normalized: {normalized_agent_phone})")
        print(f"   Active: {agent.get('active')}")
        print(f"   Direction: {agent.get('direction')}")
        
        if normalized_agent_phone == normalized_target:
            print("   ✅ MATCH FOUND!")
            found = True
            if not agent.get('active'):
                print("   ⚠️ BUT AGENT IS INACTIVE!")
        else:
            print("   ❌ No match")

    if not found:
        print("\n❌ NO AGENT FOUND for this phone number!")

if __name__ == "__main__":
    asyncio.run(check_agents())
