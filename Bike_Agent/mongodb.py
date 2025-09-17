# mongodb.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import certifi
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables from .env
load_dotenv()

def get_mongo_client():
    """
    Create and return a MongoDB client with proper error handling.
    Ensures the URI is valid and special characters in password are encoded.
    """
    try:
        # Fetch credentials from environment variables
        username = os.environ.get("MONGO_USER") or "vikas"
        password = os.environ.get("MONGO_PASSWORD") or "j4x83g46B_Q%6*e"
        password_encoded = quote_plus(password)

        # Construct MongoDB Atlas URI
        mongodb_uri = f"mongodb+srv://{username}:{password_encoded}@cluster0.srjm2rk.mongodb.net/car_service_db?retryWrites=true&w=majority"

        print(f"🔗 Attempting connection: {mongodb_uri}")  # For debugging

        # Create MongoDB client
        client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsCAFile=certifi.where(),
            connectTimeoutMS=10000,
            serverSelectionTimeoutMS=10000
        )

        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas")

        # Test database access
        db = client["car_service_db"]
        collections = db.list_collection_names()
        print(f"📊 Available collections: {collections}")

        return client

    except OperationFailure as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Check your username/password in the connection string or MongoDB Atlas user permissions")
        return None
    except ConnectionFailure as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Check your internet connection and IP whitelist in MongoDB Atlas")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

# Quick test
if __name__ == "__main__":
    client = get_mongo_client()
    if client:
        print("🎉 MongoDB connection test successful!")
    else:
        print("💥 MongoDB connection test failed!")
