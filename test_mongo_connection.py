#!/usr/bin/env python3
"""
Test script to diagnose MongoDB connection issues
"""

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "voiceagent")

async def test_mongodb_connection():
    """Test MongoDB connection and provide detailed diagnostics"""
    
    print("="*60)
    print("MongoDB Connection Test")
    print("="*60)
    print()
    
    # Check if URL is set
    if not MONGODB_URL or MONGODB_URL.strip() == "":
        print("❌ ERROR: MONGODB_URL is not set in .env file")
        print("   Please add MONGODB_URL to your .env file")
        return False
    
    print(f"✓ MongoDB URL found: {MONGODB_URL[:50]}...")
    print(f"✓ Database name: {MONGODB_DATABASE}")
    print()
    
    # Try to connect with different timeout settings
    print("Attempting to connect to MongoDB...")
    print()
    
    try:
        # Create client with longer timeout for diagnostic purposes
        client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=30000,  # 30 seconds for testing
            connectTimeoutMS=30000,
            tlsAllowInvalidCertificates=True  # Fix for macOS SSL certificate issue
        )
        
        print("✓ MongoDB client created")
        
        # Try to ping the server
        print("Sending ping command...")
        await client.admin.command('ping')
        
        print("✅ SUCCESS: MongoDB connection successful!")
        print()
        
        # Get database
        db = client[MONGODB_DATABASE]
        
        # List collections
        print(f"Listing collections in '{MONGODB_DATABASE}' database...")
        collection_names = await db.list_collection_names()
        
        if collection_names:
            print(f"✓ Found {len(collection_names)} collections:")
            for name in collection_names:
                count = await db[name].count_documents({})
                print(f"   - {name}: {count} documents")
        else:
            print("⚠️  No collections found (database might be new)")
        
        print()
        print("="*60)
        print("✅ MongoDB is working correctly!")
        print("="*60)
        
        client.close()
        return True
        
    except ServerSelectionTimeoutError as e:
        print(f"❌ ERROR: Could not connect to MongoDB server")
        print(f"   Error: {e}")
        print()
        print("Possible causes:")
        print("   1. IP address not whitelisted in MongoDB Atlas")
        print("   2. Network connectivity issues")
        print("   3. MongoDB cluster is down or unreachable")
        print()
        print("Solutions:")
        print("   1. Go to MongoDB Atlas > Network Access > Add IP Address")
        print("   2. Add '0.0.0.0/0' to allow all IPs (for testing)")
        print("   3. Or add your current IP address")
        return False
        
    except ConnectionFailure as e:
        print(f"❌ ERROR: Connection failed")
        print(f"   Error: {e}")
        print()
        print("Possible causes:")
        print("   1. Invalid credentials")
        print("   2. Database user doesn't have proper permissions")
        print("   3. Connection string is incorrect")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: Unexpected error")
        print(f"   Type: {type(e).__name__}")
        print(f"   Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_mongodb_connection())
    exit(0 if result else 1)
