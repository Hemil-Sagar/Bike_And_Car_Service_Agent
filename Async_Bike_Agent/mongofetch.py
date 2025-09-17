import os
import datetime
from urllib.parse import quote_plus
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# --- Global Client Instance ---
# Best practice is to create a single client instance and reuse it.
# This avoids the overhead of connecting to the DB on every function call.
_mongo_client: Optional[AsyncIOMotorClient] = None

# --- Utility to get or create a MongoDB async client ---
def get_db_client() -> AsyncIOMotorClient:
    """
    Returns a singleton instance of the async MongoDB client.
    Initializes the client if it doesn't exist.
    """
    global _mongo_client
    if _mongo_client is None:
        try:
            username = os.environ.get("MONGO_USER", "vikas")
            password = os.environ.get("MONGO_PASSWORD", "j4x83g46B_Q%6*e")
            password_encoded = quote_plus(password)

            mongodb_uri = (
                f"mongodb+srv://{username}:{password_encoded}"
                "@cluster0.srjm2rk.mongodb.net/car_service_db?retryWrites=true&w=majority"
            )
            # Use the async client from motor
            _mongo_client = AsyncIOMotorClient(mongodb_uri)
            print("MongoDB async client initialized.")
        except Exception as e:
            print(f"Error creating Mongo async client: {e}")
            raise  # Re-raise the exception to be handled by the application
    return _mongo_client

async def close_db_client():
    """Closes the MongoDB client connection."""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        print("MongoDB async client closed.")

# --- Fetch user details by phone number (Async) ---
async def get_user_data(phone_number: str) -> Optional[dict]:
    """
    Asynchronously fetch a user document by phone_number.
    """
    client = get_db_client()
    try:
        db = client["car_service_db"]
        collection = db["users"]
        # Use await for the database operation
        return await collection.find_one({"phone_number": phone_number})
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return None
    # No client.close() needed here

# --- Fetch car service details by car number (Async) ---
async def get_car_service_data(car_number: str) -> Optional[dict]:
    """
    Asynchronously fetch a car service document by car_number.
    """
    client = get_db_client()
    try:
        db = client["car_service_db"]
        collection = db["car_services"]
        return await collection.find_one({"car_number": car_number})
    except Exception as e:
        print(f"Error fetching service data: {e}")
        return None

# --- Update the next service date for a car (Async) ---
async def update_service_date(car_number: str, new_date: datetime.datetime) -> bool:
    """
    Asynchronously update next_service_date for the given car_number.
    """
    client = get_db_client()
    try:
        db = client["car_service_db"]
        collection = db["car_services"]
        result = await collection.update_one(
            {"car_number": car_number},
            {"$set": {
                "next_service_date": new_date,
                "updated_at": datetime.datetime.utcnow()
            }},
            upsert=True
        )
        return result.modified_count > 0 or result.matched_count > 0
    except Exception as e:
        print(f"Error updating service date: {e}")
        return False

# --- Add selected services for a car (Async) ---
async def add_selected_services(car_number: str, services_list: list) -> bool:
    """
    Asynchronously add additional selected services to the car_services document.
    """
    client = get_db_client()
    try:
        db = client["car_service_db"]
        collection = db["car_services"]

        # Normalization logic is synchronous and does not need changes
        if isinstance(services_list, str):
            normalized = [services_list.strip()] if services_list.strip() else []
        elif isinstance(services_list, (list, tuple, set)):
            normalized = [str(s).strip() for s in services_list if str(s).strip()]
        else:
            normalized = [str(services_list).strip()] if str(services_list).strip() else []

        if not normalized:
            return False

        result = await collection.update_one(
            {"car_number": car_number},
            {
                "$addToSet": {"selected_services": {"$each": normalized}},
                "$set": {"updated_at": datetime.datetime.utcnow()}
            },
            upsert=True
        )
        return (
            result.modified_count > 0
            or bool(getattr(result, "upserted_id", None))
            or result.matched_count > 0
        )
    except Exception as e:
        print(f"Error adding selected services: {e}")
        return False