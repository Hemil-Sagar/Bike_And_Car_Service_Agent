# Download the helper library from https://www.twilio.com/docs/python/install
import os
import asyncio
from twilio.rest import Client
from twilio.http.async_http_client import AsyncTwilioHttpClient # Import the async client
from dotenv import load_dotenv

load_dotenv()

# --- Best Practice: Load credentials from environment variables ---
# It's recommended to use environment variables for security.
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "ACfda927f41d33a99d551c4903e69bc8d7")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "b7d7cc7cb0715ff8aef9f3676f946a9d")
FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "+14452817649")
TO_NUMBER = os.environ.get("TWILIO_TO_NUMBER", "+919428192520")

# --- Initialize the Async Client ---
try:
    # 1. Create an instance of the async HTTP client
    async_http_client = AsyncTwilioHttpClient()
    
    # 2. Pass it to the main Twilio Client during initialization
    client = Client(ACCOUNT_SID, AUTH_TOKEN, http_client=async_http_client)
    print("✅ Twilio async client initialized successfully.")
    
except Exception as e:
    print(f"❌ Error initializing Twilio async client: {e}")
    raise

# --- Define the Asynchronous Function ---
async def make_webhook_call(webhook_url: str):
    """
    Asynchronously make a call using a webhook URL.
    
    Args:
        webhook_url (str): The webhook URL to use for the call.
        
    Returns:
        str: The call SID.
    """
    print(f"📞 Attempting to make a call to {TO_NUMBER}...")
    try:
        # 3. Use 'await' for the API call
        call = await client.calls.create(
            url=f"{webhook_url}/voice",
            from_=FROM_NUMBER,
            to=TO_NUMBER,
            status_callback=f"{webhook_url}/status",
            status_callback_event=['completed', 'answered', 'busy', 'failed', 'no-answer']
        )
        print(f"✅ Call initiated successfully!")
        return call.sid
    except Exception as e:
        print(f"❌ Error making webhook call: {e}")
        raise

# --- Main Execution Block ---
async def main():
    """Main function to run the async call."""
    # Replace with your actual ngrok URL or load from environment
    webhook_url = os.environ.get("WEBHOOK_URL", "https://3582b96f78cc.ngrok-free.app")
    
    if "ngrok-free.app" in webhook_url:
        print(f"⚠️  Using ngrok URL: {webhook_url}")
        print("Ensure your ngrok tunnel and local server are running.")
        
    call_sid = await make_webhook_call(webhook_url)
    print(f"🔊 Webhook Call SID: {call_sid}")

# 4. Run the main async function using asyncio
if __name__ == "__main__":
    asyncio.run(main())