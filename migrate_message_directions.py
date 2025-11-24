#!/usr/bin/env python3
"""
Migration script to add direction and role fields to existing messages
This will update all messages in MongoDB that are missing these fields
"""

import asyncio
import logging
from databases.mongodb_db import get_mongo_db, is_mongodb_available

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_messages():
    """Add direction and role fields to existing messages"""
    if not is_mongodb_available():
        logger.error("MongoDB is not available")
        return
    
    try:
        db = get_mongo_db()
        if db is None:
            logger.error("Could not get MongoDB database")
            return
        
        collection = db["messages"]
        
        # Get all documents
        cursor = collection.find({})
        
        total_docs = 0
        total_messages_updated = 0
        
        async for doc in cursor:
            total_docs += 1
            agent_id = doc.get("agent_id")
            messages = doc.get("messages", [])
            
            logger.info(f"Processing document for agent_id: {agent_id} with {len(messages)} messages")
            
            updated_messages = []
            messages_changed = 0
            
            for msg in messages:
                # Create a copy of the message
                updated_msg = dict(msg)
                
                # Check if direction field is missing
                if "direction" not in updated_msg:
                    # Determine direction based on which number fields are set
                    # If user_number is in from_number or msg has from_number != agent_id, it's inbound
                    # Otherwise it's outbound
                    
                    user_number = updated_msg.get("user_number")
                    agent_number = updated_msg.get("agent_number")
                    from_number = updated_msg.get("from_number")
                    to_number = updated_msg.get("to_number")
                    
                    # Logic: if user_number exists, use it to determine direction
                    if user_number and agent_number:
                        # If user_number was the sender (from), it's inbound
                        # If agent_number was the sender (from), it's outbound
                        # We need to check against from_number if available
                        if from_number == user_number or (from_number and from_number != agent_id):
                            updated_msg["direction"] = "inbound"
                        else:
                            updated_msg["direction"] = "outbound"
                    elif from_number and to_number:
                        # Fallback: if from_number is the agent, it's outbound
                        if from_number == agent_id:
                            updated_msg["direction"] = "outbound"
                        else:
                            updated_msg["direction"] = "inbound"
                    else:
                        # Default to outbound if we can't determine (since most existing messages are agent responses)
                        updated_msg["direction"] = "outbound"
                        logger.warning(f"Could not determine direction for message {updated_msg.get('message_sid')}, defaulting to outbound")
                    
                    messages_changed += 1
                    logger.info(f"  Set direction to '{updated_msg['direction']}' for message {updated_msg.get('message_sid')}")
                
                # Check if role field is missing or incorrect
                if "role" not in updated_msg or updated_msg.get("role") not in ["user", "assistant"]:
                    # Set role based on direction
                    if updated_msg.get("direction") == "inbound":
                        updated_msg["role"] = "user"
                    else:
                        updated_msg["role"] = "assistant"
                    
                    messages_changed += 1
                    logger.info(f"  Set role to '{updated_msg['role']}' for message {updated_msg.get('message_sid')}")
                
                updated_messages.append(updated_msg)
            
            # Update the document if any messages were changed
            if messages_changed > 0:
                result = await collection.update_one(
                    {"agent_id": agent_id},
                    {"$set": {"messages": updated_messages}}
                )
                
                logger.info(f"✅ Updated {messages_changed} messages for agent_id: {agent_id}")
                total_messages_updated += messages_changed
            else:
                logger.info(f"No changes needed for agent_id: {agent_id}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Migration complete!")
        logger.info(f"Total documents processed: {total_docs}")
        logger.info(f"Total messages updated: {total_messages_updated}")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(migrate_messages())
