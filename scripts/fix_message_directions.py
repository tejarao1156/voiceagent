#!/usr/bin/env python3
"""
Direct MongoDB update script to add direction field to messages that are missing it
This uses Motor (async MongoDB driver) directly
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys
from dotenv import load_dotenv

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Load environment variables from project root
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

async def update_messages_with_direction():
    """Add direction field to all messages that don't have it"""
    
    # Get MongoDB connection string
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "voiceagent")
    
    print(f"Connecting to MongoDB at {mongo_uri}")
    print(f"Database: {db_name}")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    collection = db["messages"]
    
    # Get all documents
    cursor = collection.find({})
    
    total_docs = 0
    total_messages_updated = 0
    
    async for doc in cursor:
        total_docs += 1
        agent_id = doc.get("agent_id")
        messages = doc.get("messages", [])
        
        print(f"\nProcessing agent_id: {agent_id} ({len(messages)} messages)")
        
        updated_messages = []
        changed = False
        
        for msg in messages:
            # Copy message
            updated_msg = dict(msg)
            
            # Check if direction is missing
            if "direction" not in updated_msg or updated_msg.get("direction") is None:
                # Determine direction based on the fields
                user_number = updated_msg.get("user_number")
                agent_number = updated_msg.get("agent_number", agent_id)
                
                # If user_number and agent_number are set, we can determine direction
                # In our schema:
                # - Inbound: user_number is from, agent_number is to
                # - Outbound: agent_number is from, user_number is to
                
                # Default to outbound for agent messages (most common case)
                direction = "outbound"
                
                # If the message has a role, use that
                role = updated_msg.get("role")
                if role == "user" or role == "customer":
                    direction = "inbound"
                
                updated_msg["direction"] = direction
                total_messages_updated += 1
                changed = True
                print(f"  ✓ Added direction='{direction}' to message: {msg.get('message_sid')}")
            
            # Also ensure role is set
            if "role" not in updated_msg or updated_msg.get("role") is None:
                direction = updated_msg.get("direction", "outbound")
                role = "user" if direction == "inbound" else "assistant"
                updated_msg["role"] = role
                changed = True
                print(f"  ✓ Added role='{role}' to message: {msg.get('message_sid')}")
            
            updated_messages.append(updated_msg)
        
        # Update document if changed
        if changed:
            await collection.update_one(
                {"agent_id": agent_id},
                {"$set": {"messages": updated_messages}}
            )
            print(f"✅ Updated document for agent_id: {agent_id}")
    
    print(f"\n{'='*70}")
    print(f"Migration Complete!")
    print(f"  Documents processed: {total_docs}")
    print(f"  Messages updated: {total_messages_updated}")
    print(f"{'='*70}\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(update_messages_with_direction())
