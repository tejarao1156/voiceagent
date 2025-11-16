#!/usr/bin/env python3
"""
Step-by-step validation test for messaging system
Tests all components systematically following DEVELOPMENT_INSTRUCTIONS.md
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from databases.mongodb_db import get_mongo_db, is_mongodb_available
from databases.mongodb_message_store import MongoDBMessageStore
from databases.mongodb_phone_store import MongoDBPhoneStore, normalize_phone_number
from tools.phone.twilio_phone import TwilioPhoneTool
from tools.phone.twilio_sms_handler import TwilioSMSHandler
from tools.response.conversation import ConversationalResponseTool

# Test colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(step: str, description: str):
    """Print test step header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}STEP {step}: {description}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

def print_success(message: str):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message: str):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {message}{RESET}")

def print_info(message: str):
    """Print info message"""
    print(f"ℹ️  {message}")

async def test_mongodb_connection():
    """Test 1: MongoDB Connection"""
    print_test("1", "MongoDB Connection")
    
    try:
        available = is_mongodb_available()
        if not available:
            print_error("MongoDB is not available")
            return False
        
        db = get_mongo_db()
        if db is None:
            print_error("Failed to get MongoDB database")
            return False
        
        # Test connection by listing collections
        collections = await db.list_collection_names()
        print_success(f"MongoDB connected successfully")
        print_info(f"Available collections: {collections}")
        
        # Check if messages collection exists
        if "messages" in collections:
            print_info("'messages' collection exists")
        else:
            print_info("'messages' collection will be created on first access")
        
        return True
    except Exception as e:
        print_error(f"MongoDB connection failed: {e}")
        return False

async def test_message_store_initialization():
    """Test 2: Message Store Initialization"""
    print_test("2", "Message Store Initialization")
    
    try:
        message_store = MongoDBMessageStore()
        print_success("MongoDBMessageStore initialized")
        
        # Test collection access (should create if doesn't exist)
        collection = message_store._get_collection()
        if collection is None:
            print_error("Failed to get collection")
            return False
        
        print_success("Collection accessed successfully (created if needed)")
        return True
    except Exception as e:
        print_error(f"Message store initialization failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def test_conversation_id_creation():
    """Test 3: Conversation ID Creation"""
    print_test("3", "Conversation ID Creation (New Conversation)")
    
    try:
        message_store = MongoDBMessageStore()
        
        # Test creating a new conversation
        from_number = "+1234567890"
        to_number = "+0987654321"
        agent_id = "+0987654321"
        
        conversation_id = await message_store.get_or_create_conversation_id(
            from_number, to_number, agent_id
        )
        
        if not conversation_id:
            print_error("Failed to create conversation ID")
            return False
        
        print_success(f"Created new conversation ID: {conversation_id}")
        print_info(f"From: {from_number}, To: {to_number}, Agent: {agent_id}")
        
        # Test retrieving existing conversation
        existing_id = await message_store.get_or_create_conversation_id(
            from_number, to_number, agent_id
        )
        
        if existing_id != conversation_id:
            print_error(f"Retrieved conversation ID doesn't match: {existing_id} != {conversation_id}")
            return False
        
        print_success(f"Retrieved existing conversation ID: {existing_id}")
        return True
    except Exception as e:
        print_error(f"Conversation ID creation failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def test_message_storage():
    """Test 4: Message Storage (Inbound and Outbound)"""
    print_test("4", "Message Storage")
    
    try:
        message_store = MongoDBMessageStore()
        
        # Test storing inbound message
        from_number = "+1234567890"
        to_number = "+0987654321"
        agent_id = "+0987654321"
        message_body = "Hello, this is a test message!"
        message_sid = f"SM{datetime.utcnow().timestamp()}"
        
        print_info("Storing inbound message...")
        stored = await message_store.create_message(
            message_sid=message_sid,
            from_number=from_number,
            to_number=to_number,
            body=message_body,
            agent_id=agent_id
        )
        
        if not stored:
            print_error("Failed to store inbound message")
            return False
        
        print_success(f"Stored inbound message: {message_sid}")
        
        # Get conversation_id for outbound message
        conversation_id = await message_store.get_conversation_id(from_number, to_number, agent_id)
        print_info(f"Using conversation_id: {conversation_id}")
        
        # Test storing outbound message
        outbound_sid = f"SM{datetime.utcnow().timestamp()}"
        response_body = "This is a test response!"
        
        print_info("Storing outbound message...")
        outbound_stored = await message_store.create_outbound_message(
            message_sid=outbound_sid,
            from_number=to_number,
            to_number=from_number,
            body=response_body,
            agent_id=agent_id,
            conversation_id=conversation_id
        )
        
        if not outbound_stored:
            print_error("Failed to store outbound message")
            return False
        
        print_success(f"Stored outbound message: {outbound_sid}")
        return True
    except Exception as e:
        print_error(f"Message storage failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def test_conversation_history():
    """Test 5: Conversation History Retrieval"""
    print_test("5", "Conversation History Retrieval")
    
    try:
        message_store = MongoDBMessageStore()
        
        from_number = "+1234567890"
        to_number = "+0987654321"
        agent_id = "+0987654321"
        
        # Get conversation history
        history = await message_store.get_conversation_history(
            from_number=from_number,
            to_number=to_number,
            agent_id=agent_id,
            limit=50
        )
        
        print_info(f"Retrieved {len(history)} message(s) from conversation history")
        
        if len(history) > 0:
            print_success("Conversation history retrieved successfully")
            for i, msg in enumerate(history[:3], 1):  # Show first 3
                role = msg.get("role", "unknown")
                body = msg.get("body", "")[:50]
                print_info(f"  {i}. [{role}] {body}...")
            if len(history) > 3:
                print_info(f"  ... and {len(history) - 3} more message(s)")
        else:
            print_warning("No conversation history found (this is OK for new conversations)")
        
        return True
    except Exception as e:
        print_error(f"Conversation history retrieval failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def test_get_conversations():
    """Test 6: Get All Conversations"""
    print_test("6", "Get All Conversations (Grouped by conversation_id)")
    
    try:
        message_store = MongoDBMessageStore()
        
        # Get all conversations
        conversations = await message_store.get_conversations(limit=100)
        
        print_info(f"Retrieved {len(conversations)} conversation(s)")
        
        if len(conversations) > 0:
            print_success("Conversations retrieved successfully")
            for i, conv in enumerate(conversations[:3], 1):  # Show first 3
                conv_id = conv.get("conversation_id", "unknown")
                message_count = conv.get("message_count", 0)
                latest = conv.get("latest_message", "")[:50]
                print_info(f"  {i}. Conversation {conv_id}: {message_count} message(s), latest: '{latest}...'")
            if len(conversations) > 3:
                print_info(f"  ... and {len(conversations) - 3} more conversation(s)")
        else:
            print_warning("No conversations found (this is OK if no messages have been sent)")
        
        return True
    except Exception as e:
        print_error(f"Get conversations failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def test_sms_handler_initialization():
    """Test 7: SMS Handler Initialization"""
    print_test("7", "SMS Handler Initialization")
    
    try:
        # Initialize conversation tool
        conversation_tool = ConversationalResponseTool()
        print_success("ConversationalResponseTool initialized")
        
        # Initialize SMS handler
        sms_handler = TwilioSMSHandler(conversation_tool)
        print_success("TwilioSMSHandler initialized")
        
        return True
    except Exception as e:
        print_error(f"SMS handler initialization failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def test_phone_store_integration():
    """Test 8: Phone Store Integration"""
    print_test("8", "Phone Store Integration (Check Registered Numbers)")
    
    try:
        phone_store = MongoDBPhoneStore()
        
        # Get all registered phones (active and inactive)
        phones = await phone_store.list_phones(active_only=False)
        
        print_info(f"Found {len(phones)} registered phone number(s)")
        
        if len(phones) > 0:
            print_success("Phone store integration working")
            for i, phone in enumerate(phones[:3], 1):  # Show first 3
                number = phone.get("phoneNumber", "unknown")
                active = phone.get("isActive", False)
                status = "active" if active else "inactive"
                print_info(f"  {i}. {number} ({status})")
            if len(phones) > 3:
                print_info(f"  ... and {len(phones) - 3} more phone(s)")
        else:
            print_warning("No registered phone numbers found (register a number to test messaging)")
        
        return True
    except Exception as e:
        print_error(f"Phone store integration failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def test_agent_config_loading():
    """Test 9: Agent Config Loading (Messaging Direction)"""
    print_test("9", "Agent Config Loading (Messaging Direction)")
    
    try:
        twilio_phone_tool = TwilioPhoneTool()
        
        # Try to load a messaging agent (if any exist)
        # We'll use a test number
        test_number = "+0987654321"
        
        agent_config = await twilio_phone_tool._load_agent_config(
            test_number, 
            direction="messaging"
        )
        
        if agent_config:
            print_success(f"Messaging agent config loaded for {test_number}")
            print_info(f"  Agent name: {agent_config.get('name', 'unknown')}")
            print_info(f"  Active: {agent_config.get('active', False)}")
            print_info(f"  Direction: {agent_config.get('direction', 'unknown')}")
        else:
            print_warning(f"No messaging agent found for {test_number} (this is OK if not configured)")
            print_info("  To test messaging, create a messaging agent for a registered number")
        
        return True
    except Exception as e:
        print_error(f"Agent config loading failed: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

async def run_all_tests():
    """Run all validation tests"""
    print(f"\n{GREEN}{'='*70}{RESET}")
    print(f"{GREEN}MESSAGING SYSTEM VALIDATION TEST SUITE{RESET}")
    print(f"{GREEN}{'='*70}{RESET}")
    print(f"\n{BLUE}Testing all components step by step...{RESET}\n")
    
    tests = [
        ("MongoDB Connection", test_mongodb_connection),
        ("Message Store Initialization", test_message_store_initialization),
        ("Conversation ID Creation", test_conversation_id_creation),
        ("Message Storage", test_message_storage),
        ("Conversation History", test_conversation_history),
        ("Get All Conversations", test_get_conversations),
        ("SMS Handler Initialization", test_sms_handler_initialization),
        ("Phone Store Integration", test_phone_store_integration),
        ("Agent Config Loading", test_agent_config_loading),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}TEST SUMMARY{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✅ PASSED{RESET}" if result else f"{RED}❌ FAILED{RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 All tests passed! Messaging system is working correctly.{RESET}\n")
        return 0
    else:
        print(f"\n{YELLOW}⚠️  Some tests failed. Please review the errors above.{RESET}\n")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

