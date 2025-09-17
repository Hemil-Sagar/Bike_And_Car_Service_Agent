# mongodb_async.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure
import certifi
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from typing import Optional

# Load environment variables from .env
load_dotenv()

# Global variable to hold the client instance (singleton pattern)
_mongo_client: Optional[AsyncIOMotorClient] = None

async def get_mongo_client() -> Optional[AsyncIOMotorClient]:
    """
    Create and return a single, reusable async MongoDB client instance.
    Includes proper error handling and connection testing.
    """
    global _mongo_client
    # Return the existing client if it's already connected
    if _mongo_client:
        return _mongo_client

    try:
        # Fetch credentials from environment variables
        username = os.environ.get("MONGO_USER") or "vikas"
        password = os.environ.get("MONGO_PASSWORD") or "j4x83g46B_Q%6*e"
        password_encoded = quote_plus(password)

        # Construct MongoDB Atlas URI
        mongodb_uri = f"mongodb+srv://{username}:{password_encoded}@cluster0.srjm2rk.mongodb.net/car_service_db?retryWrites=true&w=majority"

        print(f"🔗 Attempting async connection: {mongodb_uri}")

        # Create async MongoDB client using motor
        client = AsyncIOMotorClient(
            mongodb_uri,
            tls=True,
            tlsCAFile=certifi.where(),
            connectTimeoutMS=10000,
            serverSelectionTimeoutMS=10000
        )

        # Test connection asynchronously
        await client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas (async)")

        # Test database access
        db = client["car_service_db"]
        collections = await db.list_collection_names()
        print(f"📊 Available collections: {collections}")

        # Store the client instance globally
        _mongo_client = client
        return _mongo_client

    except OperationFailure as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Check your username/password or MongoDB Atlas user permissions")
        return None
    except ConnectionFailure as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Check your internet connection and IP whitelist in MongoDB Atlas")
        return None
    except Exception as e:
        print(f"❌ Unexpected async error: {e}")
        return None

async def close_mongo_client():
    """
    Close the shared MongoDB client connection.
    """
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        print("🔌 MongoDB async client connection closed.")

# --- Asynchronous Test Block ---
async def main():
    """Main async function to run the connection test."""
    print("--- Running async MongoDB connection test ---")
    client = await get_mongo_client()
    if client:
        print("\n🎉 MongoDB async connection test successful!")
        # Example: Access a collection
        db = client.car_service_db
        user_count = await db.users.count_documents({})
        print(f"Found {user_count} documents in 'users' collection.")
    else:
        print("\n💥 MongoDB async connection test failed!")
    
    # Clean up the connection
    await close_mongo_client()

if __name__ == "__main__":
    # Use asyncio.run() to execute the async main function
    asyncio.run(main())