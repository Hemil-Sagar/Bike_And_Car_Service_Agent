# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say
from dotenv import load_dotenv
load_dotenv()

# account_sid = os.environ["TWILIO_SID"]
# auth_token = os.environ["TWILIO_AUTH"]
# from_number = os.environ["TWILIO_NUMBER"]
# to_number = +919428192520

# getting the detail from env and setting the details into the current environment

# account_sid=os.getenv("TWILIO_SID")
# os.environ[TWILIO_SID]=account_sid
# print(TWILIO_SID)

# auth_token=os.getenv("TWILIO_AUTH")
# os.environ["TWILIO_AUTH"]=auth_token
# print(TWILIO_AUTH)

# from_number=os.getenv("TWILIO_NUMBER")
# os.environ["TWILIO_NUMBER"]=from_number
# print(TWILIO_NUMBER)

# to_number=os.getenv("TO_NUMBER")
# os.environ["TO_NUMBER"]=to_number
# print(TO_NUMBER)


# webhook_url=os.getenv("NGROK_URL")
# os.environ["NGROK_URL"]=webhook_url
# print(NGROK_URL)






try:
    client = Client("ACfda927f41d33a99d551c4903e69bc8d7", "b7d7cc7cb0715ff8aef9f3676f946a9d")
except Exception as e:
    print(f"Error initializing Twilio client: {e}")
    raise


def make_webhook_call(webhook_url):
    """
    Make a call using a webhook URL
    
    Args:
        webhook_url (str): The webhook URL to use for the call
        
    Returns:
        str: The call SID
    """
    try:
        call = client.calls.create(
            url=f"{webhook_url}/voice",
            from_="+14452817649",
            to="+919726816555",
            status_callback=f"{webhook_url}/status",
            status_callback_event=['completed', 'answered', 'busy', 'failed', 'no-answer']
        )
        return call.sid
    except Exception as e:
        print(f"Error making webhook call: {e}")
        raise

# Example webhook usage (uncomment and modify the URL):
webhook_url = "https://ef1337499577.ngrok-free.app"  # Replace with your actual ngrok URL
call_sid = make_webhook_call(webhook_url)
print(f"Webhook Call SID: {call_sid}")