from pymongo import MongoClient
from urllib.parse import quote_plus
import os
import datetime

# --- Utility to create a MongoDB client ---
def get_mongo_client():
    """
    Creates and returns a MongoDB client using Atlas credentials.
    """
    try:
        username = os.environ.get("MONGO_USER", "vikas")
        password = os.environ.get("MONGO_PASSWORD", "j4x83g46B_Q%6*e")
        password_encoded = quote_plus(password)

        mongodb_uri = (
            f"mongodb+srv://{username}:{password_encoded}"
            "@cluster0.srjm2rk.mongodb.net/car_service_db?retryWrites=true&w=majority"
        )
        return MongoClient(mongodb_uri)
    except Exception as e:
        print(f"Error creating Mongo client: {e}")
        return None


# --- Fetch user details by phone number ---
def get_user_data(phone_number):
    """
    Fetch a user document by phone_number.
    """
    client = get_mongo_client()
    if not client:
        return None
    try:
        db = client["car_service_db"]
        collection = db["users"]
        return collection.find_one({"phone_number": phone_number})
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return None
    finally:
        client.close()


# --- Fetch car service details by car number ---
def get_car_service_data(car_number):
    """
    Fetch a car service document by car_number.
    """
    client = get_mongo_client()
    if not client:
        return None
    try:
        db = client["car_service_db"]
        collection = db["car_services"]
        return collection.find_one({"car_number": car_number})
    except Exception as e:
        print(f"Error fetching service data: {e}")
        return None
    finally:
        client.close()


# --- Update the next service date for a car ---
def update_service_date(car_number, new_date):
    """
    Update next_service_date for the given car_number.
    """
    client = get_mongo_client()
    if not client:
        return False
    try:
        db = client["car_service_db"]
        collection = db["car_services"]
        result = collection.update_one(
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
    finally:
        client.close()


# --- Add selected services for a car ---
def add_selected_services(car_number, services_list):
    """
    Add additional selected services to the car_services document.
    """
    client = get_mongo_client()
    if not client:
        return False
    try:
        db = client["car_service_db"]
        collection = db["car_services"]

        # Normalize input to a list of clean strings
        if isinstance(services_list, str):
            normalized = [services_list.strip()] if services_list.strip() else []
        elif isinstance(services_list, (list, tuple, set)):
            normalized = [str(s).strip() for s in services_list if str(s).strip()]
        else:
            normalized = [str(services_list).strip()] if str(services_list).strip() else []

        if not normalized:
            return False

        result = collection.update_one(
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
    finally:
        client.close()
