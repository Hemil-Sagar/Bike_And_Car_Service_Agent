import os
import logging
from datetime import datetime, timedelta

# --- Core FastAPI & Starlette Imports ---
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

# --- Twilio Imports ---
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.request_validator import RequestValidator

# --- Environment and Configuration ---
from dotenv import load_dotenv

# --- External Async Utilities (MUST BE UPDATED TO ASYNC) ---
from model import summarize, is_bye, want_admission, is_yes, detect_language, extract_dates
from google_tts import GoogleCloudTTS
from mongofetch import get_user_data, get_car_service_data, update_service_date, add_selected_services

# --- Load Environment and Credentials ---
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"/home/hemil/Desktop/agent/service-account-key.json"
load_dotenv()

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
VALIDATE_REQUESTS = os.environ.get("VALIDATE_REQUESTS", "false").lower() == "true"

# --- Initialize Utilities ---
tts = GoogleCloudTTS(cache_dir="static/audio_cache")
app = FastAPI()
validator = RequestValidator(TWILIO_AUTH_TOKEN)

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Service Catalog (Unchanged) ---
SERVICES = [
    "Air filter replacement", "Oil filter change", "Tire rotation",
    "Battery health check", "Bike wash", "Coolant top-up",
    "Headlight bulb replacement", "Brake pad inspection"
]

# --- Helper Functions (Updated for Async) ---

def parse_date_string(date_str):
    """Parse various date formats and return datetime object (Synchronous)"""
    if not date_str:
        return datetime.utcnow() + timedelta(days=30)
    try:
        formats = [
            "%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d-%m-%Y", "%d/%m/%Y",
            "%B %d, %Y", "%b %d, %Y", "%d %B", "%d %b", "%B %d", "%b %d"
        ]
        for fmt in formats:
            try:
                d = datetime.strptime(date_str.strip(), fmt)
                if d.year == 1900:
                    d = d.replace(year=datetime.now().year)
                return d
            except ValueError:
                continue
        from dateutil import parser
        return parser.parse(date_str)
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return datetime.utcnow() + timedelta(days=30)

def format_date_for_hindi_speech(date_obj):
    """Format date for Hindi speech output (Synchronous)"""
    hindi_months = [
        "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून",
        "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"
    ]
    return f"{date_obj.day} {hindi_months[date_obj.month-1]} {date_obj.year}"

def log_interaction(user_input, ai_response):
    """Log user input and AI response (Synchronous)"""
    logger.info(f"[USER SPEECH] {user_input}")
    logger.info(f"[AI RESPONSE] {ai_response}")

async def generate_tts_and_play(response_obj, text, fallback_text=None):
    """Generate TTS audio and add to Twilio response object (Asynchronous)"""
    try:
        lang = detect_language(text) or "hi-IN"
        # Assumes tts.generate_speech is now an async function
        audio_url = await tts.generate_speech(text, language_code=lang)
        if audio_url:
            response_obj.play(audio_url)
        else:
            response_obj.say(fallback_text or text, language='hi-IN')
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        response_obj.say(fallback_text or text, language='hi-IN')

async def generate_tts_for_gather(gather_obj, text, fallback_text=None):
    """Generate TTS audio and add to Twilio Gather object (Asynchronous)"""
    try:
        lang = detect_language(text) or "hi-IN"
        # Assumes tts.generate_speech is now an async function
        audio_url = await tts.generate_speech(text, language_code=lang)
        if audio_url:
            gather_obj.play(audio_url)
        else:
            gather_obj.say(fallback_text or text, language='hi-IN')
    except Exception as e:
        logger.error(f"TTS generation failed for gather: {e}")
        gather_obj.say(fallback_text or text, language='hi-IN')

# --- Middleware for Twilio Request Validation ---
@app.middleware("http")
async def validate_twilio_request_middleware(request: Request, call_next):
    if VALIDATE_REQUESTS and TWILIO_AUTH_TOKEN and request.method == "POST" and "/health" not in str(request.url):
        try:
            form_data = await request.form()
            is_valid = validator.validate(
                str(request.url),
                form_data,
                request.headers.get('X-TWILIO-SIGNATURE', '')
            )
            if not is_valid:
                logger.warning("Invalid Twilio request signature")
                return JSONResponse(content={"error": "Invalid request signature"}, status_code=403)
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return JSONResponse(content={"error": "Validation error"}, status_code=500)

    response = await call_next(request)
    return response

# --- FastAPI Routes ---

@app.get("/")
async def home():
    """Health check endpoint"""
    return {"message": "Bike Service Agent Running"}

@app.post("/voice")
async def voice():
    """Initial voice endpoint - greet user"""
    r = VoiceResponse()
    text = "Namaste! Main Sarthi Toyota ki AI agent bol rahi hoon. Aapki Bike service ke liye call kar rahi hoon."
    log_interaction("N/A (call start)", text)
    await generate_tts_and_play(r, text, "Hello! I am calling regarding your Bike service.")
    r.redirect('/Bike-number')
    return Response(content=str(r), media_type='application/xml')

@app.post("/Bike-number")
async def car_number(To: str = Form(...)):
    """Confirm Bike number with user"""
    # Assumes get_user_data is an async function
    user = await get_user_data(To)
    car = user.get('car_number', 'unknown') if user else 'unknown'
    
    r = VoiceResponse()
    text = f"Kya aapkai Bike ka number {car} hai? Kripya haan ya na mein jawab dein." if car != 'unknown' else "Hum aapki Bike ka number confirm nahi kar pa rahe. Kya aap apna Bike number bata sakte hain?"
    log_interaction("Bike number confirmation prompt", text)
    
    gather = Gather(input='speech', action='/service', speechModel="deepgram_nova-3", language='multi', timeout=10, barge_in=True)
    await generate_tts_for_gather(gather, text, "Please confirm your Bike number")
    r.append(gather)
    
    r.say("Sorry, I didn't get your response. Please call back later.", language='en')
    r.hangup()
    
    return Response(content=str(r), media_type='application/xml')

@app.post("/service")
async def service(SpeechResult: str = Form(''), To: str = Form(...)):
    """Handle Bike number confirmation and show service due date"""
    speech = SpeechResult.lower()
    r = VoiceResponse()
    user = await get_user_data(To)
    car = user.get('car_number', 'unknown') if user else 'unknown'

    log_interaction(speech, f"Processing confirmation for Bike: {car}")

    if is_yes(speech):
        svc = await get_car_service_data(car)
        if svc and 'next_service_date' in svc:
            date_str = format_date_for_hindi_speech(svc['next_service_date'])
            text = f"Aapki Bike service ki due date {date_str} thi . Kya aap dusre date ko  schedule karna chahte hai?"
        else:
            text = "Aapki Bike service next month due hai. Kya aap reschedule karna chahte hai?"
        
        log_interaction(speech, text)
        gather = Gather(input='speech', action='/reschedule', speechModel="deepgram_nova-3", language='multi', timeout=10, barge_in=True)
        await generate_tts_for_gather(gather, text, "Would you like to reschedule your service?")
        r.append(gather)
    else:
        text = "Samjha. Shayad galat number par call aaya hai. Maaf kijiye. Aapka din mangalmay ho!"
        log_interaction(speech, text)
        await generate_tts_and_play(r, text, "Sorry for the inconvenience. Have a good day!")
        r.hangup()
    
    return Response(content=str(r), media_type='application/xml')

@app.post("/reschedule")
async def reschedule(SpeechResult: str = Form('')):
    """Handle reschedule confirmation"""
    speech = SpeechResult.lower()
    r = VoiceResponse()
    log_interaction(speech, "Processing reschedule request")
    
    if is_yes(speech):
        text = "Bahut achha! Aap konse din service schedule karna chahte hai? Kripya date bataiye."
        gather = Gather(input='speech', action='/reschedule-date', speechModel="deepgram_nova-3", language='multi', timeout=15, barge_in=True)
        await generate_tts_for_gather(gather, text, "Which date would you like to reschedule to?")
        r.append(gather)
    else:
        text = "Theek hai, current date par hi service hogi. Kya aap koi additional services chahte hai?"
        await generate_tts_and_play(r, text, "Alright, service will remain on the current date.")
        r.redirect('/offer-services')
    
    log_interaction(speech, text)
    return Response(content=str(r), media_type='application/xml')

@app.post("/reschedule-date")
async def reschedule_date(SpeechResult: str = Form(''), To: str = Form(...)):
    """Handle new service date"""
    extracted_date = extract_dates(SpeechResult)
    date_obj = parse_date_string(extracted_date)
    
    user = await get_user_data(To)
    if user and user.get('car_number'):
        await update_service_date(user['car_number'], date_obj)
    
    r = VoiceResponse()
    formatted = format_date_for_hindi_speech(date_obj)
    text = f"Perfect! Aapki Bike service {formatted} ko schedule kar di gayi hai."
    log_interaction(SpeechResult, text)
    
    await generate_tts_and_play(r, text, f"Your service has been rescheduled to {date_obj.strftime('%B %d, %Y')}")
    r.redirect('/offer-services')
    
    return Response(content=str(r), media_type='application/xml')

@app.post("/offer-services")
async def offer_services():
    """Offer additional services"""
    r = VoiceResponse()
    service_list = "Air filter replacement, Oil filter change, Tire rotation, Battery health check, Car wash, Coolant top-up, Headlight bulb replacement, aur Brake pad inspection"
    text = f"Hamare paas kuch additional services bhi available hai jaise: {service_list}. Kya aap koi additional service chahte hai? Service ka naam boliye ya 'nahi' kahiye."
    log_interaction("Additional services offer", text)
    
    gather = Gather(input='speech', action='/handle-services', speechModel="deepgram_nova-3", language='multi', timeout=15, barge_in=True)
    await generate_tts_for_gather(gather, text, "Would you like any additional services?")
    r.append(gather)
    
    return Response(content=str(r), media_type='application/xml')

@app.post("/handle-services")
async def handle_services(SpeechResult: str = Form(''), To: str = Form(...)):
    """Handle selected additional services"""
    speech = SpeechResult.lower()
    logger.info(f"[USER SPEECH for services] {speech}")
    r = VoiceResponse()
    
    if any(word in speech for word in ['nahi', 'nahin', 'no', 'nothing', 'kuch nahi']):
        text = "Theek hai, sirf regular service hi hogi. Dhanyawad!"
        log_interaction(speech, text)
        await generate_tts_and_play(r, text, "Alright, only regular service then. Thank you!")
        
        final_text = "Aapka service appointment confirm ho gaya hai.. Sarthi Toyota ko choose karne ke liye dhanyawad!"
        await generate_tts_and_play(r, final_text, "Your service appointment is confirmed. Thank you for choosing us!")
        r.hangup()
        return Response(content=str(r), media_type='application/xml')

    chosen = [svc for i, svc in enumerate(SERVICES, 1) if str(i) in speech or any(word in speech for word in svc.lower().split())]
    
    if chosen:
        services_text = ', '.join(chosen)
        text = f"Bahut badhiya! Aapne ye services select ki hai: {services_text}. Ye sab services add kar di gayi hai."
        user = await get_user_data(To)
        if user and user.get('car_number'):
            await add_selected_services(user['car_number'], chosen)
    else:
        text = "Maaf kijiye, main aapki service selection samajh nahi payi. Sirf regular service confirm kar di gayi hai."
    
    log_interaction(speech, text)
    await generate_tts_and_play(r, text, "Your selected services have been added.")
    
    final_text = "Aapka service appointment complete confirm ho gaya hai. Sarthi Toyota choose karne ke liye bahut bahut dhanyawad! Aapka din shubh ho!"
    await generate_tts_and_play(r, final_text, "Your appointment is confirmed. Thank you and have a great day!")
    
    r.hangup()
    return Response(content=str(r), media_type='application/xml')


# --- Health and Status Endpoints ---
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "time": datetime.utcnow().isoformat(),
        "tts_status": "google_cloud_tts_enabled"
    }

@app.get("/status")
async def status():
    return {
        "status": "ok",
        "service": "car_service_agent",
        "version": "1.0"
    }

# --- Exception Handlers ---
@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"error": "Endpoint not found"})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Code to run on application startup"""
    cache_dir = "static/audio_cache"
    os.makedirs(cache_dir, exist_ok=True)
    logger.info("Starting Bike Service Agent server")
    logger.info(f"TTS Cache directory: {cache_dir}")
    logger.info(f"Request validation: {'Enabled' if VALIDATE_REQUESTS else 'Disabled'}")

# --- To Run This App ---
# 1. Install uvicorn: pip install uvicorn
# 2. Save the code as main.py
# 3. Run from your terminal: uvicorn main:app --host 0.0.0.0 --port 5000 --reload