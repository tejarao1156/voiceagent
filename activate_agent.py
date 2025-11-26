"""
Activate Agent
"""
import asyncio
import logging
from databases.mongodb_db import initialize_mongodb
from databases.mongodb_agent_store import MongoDBAgentStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def activate_agent():
    initialize_mongodb()
    store = MongoDBAgentStore()
    
    agent_id = "69267fc48ad5dc9528a076b8"
    print(f"\n🚀 Activating agent: {agent_id}")
    
    success = await store.update_agent(agent_id, {"active": True})
    
    if success:
        print("✅ Agent activated successfully!")
    else:
        print("❌ Failed to activate agent")

if __name__ == "__main__":
    asyncio.run(activate_agent())
