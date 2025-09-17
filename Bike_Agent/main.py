from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.request_validator import RequestValidator
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import logging

# --- External utilities ---
from model import summarize, is_bye, want_admission, is_yes, detect_language, extract_dates
from google_tts import GoogleCloudTTS
from mongofetch import get_user_data, get_car_service_data, update_service_date, add_selected_services

# Load environment and credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"/home/hemil/Desktop/agent/service-account-key.json"
load_dotenv()

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
VALIDATE_REQUESTS = os.environ.get("VALIDATE_REQUESTS", "false").lower() == "true"

# Initialize Google TTS
tts = GoogleCloudTTS(cache_dir="static/audio_cache")

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service catalog
SERVICES = [
    "Air filter replacement",
    "Oil filter change", 
    "Tire rotation",
    "Battery health check",
    "Bike wash",
    "Coolant top-up",
    "Headlight bulb replacement",
    "Brake pad inspection"
]

# --- Helper Functions ---

def parse_date_string(date_str):
    """Parse various date formats and return datetime object"""
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
                
        # Try dateutil parser as fallback
        from dateutil import parser
        return parser.parse(date_str)
        
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return datetime.utcnow() + timedelta(days=30)

def format_date_for_hindi_speech(date_obj):
    """Format date for Hindi speech output"""
    hindi_months = [
        "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून",
        "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"
    ]
    return f"{date_obj.day} {hindi_months[date_obj.month-1]} {date_obj.year}"

def log_interaction(user_input, ai_response):
    """Log user input and AI response"""
    logger.info(f"[USER SPEECH] {user_input}")
    logger.info(f"[AI RESPONSE] {ai_response}")

def generate_tts_and_play(response_obj, text, fallback_text=None):
    """Generate TTS audio and add to Twilio response object"""
    try:
        # Detect language for TTS
        lang = detect_language(text) or "hi-IN"  # Default to Hindi
        
        # Generate TTS audio
        audio_url = tts.generate_speech(text, language_code=lang)
        
        if audio_url:
            response_obj.play(audio_url)
        else:
            # Fallback to Twilio's built-in TTS
            response_obj.say(fallback_text or text, language='hi-IN')
            
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        # Fallback to Twilio's built-in TTS
        response_obj.say(fallback_text or text, language='hi-IN')

def generate_tts_for_gather(gather_obj, text, fallback_text=None):
    """Generate TTS audio and add to Twilio Gather object"""
    try:
        # Detect language for TTS
        lang = detect_language(text) or "hi-IN"  # Default to Hindi
        
        # Generate TTS audio
        audio_url = tts.generate_speech(text, language_code=lang)
        
        if audio_url:
            gather_obj.play(audio_url)
        else:
            # Fallback to Twilio's built-in TTS
            gather_obj.say(fallback_text or text, language='hi-IN')
            
    except Exception as e:
        logger.error(f"TTS generation failed for gather: {e}")
        # Fallback to Twilio's built-in TTS
        gather_obj.say(fallback_text or text, language='hi-IN')

# --- Middleware ---

def validate_twilio_request():
    """Validate incoming Twilio requests"""
    if not VALIDATE_REQUESTS or not TWILIO_AUTH_TOKEN:
        return True
        
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    return validator.validate(
        str(request.url), 
        request.form, 
        request.headers.get('X-TWILIO-SIGNATURE', '')
    )

@app.before_request
def before_request():
    """Validate requests before processing"""
    if request.method == 'POST' and not validate_twilio_request():
        logger.warning("Invalid Twilio request signature")
        return jsonify({"error": "Invalid request signature"}), 403

# --- Routes ---

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return "Bike Service Agent Running"

@app.route('/voice', methods=['POST'])
def voice():
    """Initial voice endpoint - greet user"""
    r = VoiceResponse()
    text = "Namaste! Main Sarthi TVS ki AI agent bol rahi hoon. Aapki Bike service ke liye call kar rahi hoon."
    
    log_interaction("N/A (call start)", text)
    
    # Use TTS for greeting
    generate_tts_and_play(r, text, "Hello! I am calling regarding your Bike service.")
    
    # Redirect to Bike number confirmation
    r.redirect('/car-number')
    return str(r)

@app.route('/car-number', methods=['POST'])
def car_number():
    """Confirm Bike number with user"""
    phone = request.values.get('To', '')
    user = get_user_data(phone)
    car = user.get('car_number', 'unknown') if user else 'unknown'
    
    r = VoiceResponse()
    
    if car != 'unknown':
        text = f"Kya aapki Bike ka number {car} hai? Kripya haan ya na mein jawab dein."
    else:
        text = "Hum aapki Bike ka number confirm nahi kar pa rahe. Kya aap apna Bike number bata sakte hain?"
    
    log_interaction("Bike number confirmation prompt", text)
    
    gather = Gather(
        input='speech',
        action='/service',
        speechModel="deepgram_nova-3",
        language='multi',
        timeout=10,
        barge_in=True
    )
    
    generate_tts_for_gather(gather, text, "Please confirm your Bike number")
    
    r.append(gather)
    
    # Fallback if no response
    r.say("Sorry, I didn't get your response. Please call back later.", language='en')
    r.hangup()
    
    return str(r)

@app.route('/service', methods=['POST'])
def service():
    """Handle Bike number confirmation and show service due date"""
    speech = request.values.get('SpeechResult', '').lower()
    r = VoiceResponse()
    phone = request.values.get('To', '')
    user = get_user_data(phone)
    car = user.get('car_number', 'unknown') if user else 'unknown'

    log_interaction(speech, f"Processing confirmation for Bike: {car}")

    if is_yes(speech):
        # Get service data
        svc = get_car_service_data(car)
        
        if svc and 'next_service_date' in svc:
            date_str = format_date_for_hindi_speech(svc['next_service_date'])
            text = f"Aapki Bike service ki due date {date_str} hai. Kya aap ye date reschedule karna chahte hai?"
        else:
            text = "Aapki Bike service next month due hai. Kya aap reschedule karna chahte hai?"
        
        log_interaction(speech, text)
        
        gather = Gather(
            input='speech',
            action='/reschedule',
            speechModel="deepgram_nova-3",
            language='multi',
            timeout=10,
            barge_in=True
        )
        
        generate_tts_for_gather(gather, text, "Would you like to reschedule your service?")
        r.append(gather)
        
    else:
        text = "Samjha. Shayad galat number par call aaya hai. Maaf kijiye. Aapka din mangalmay ho!"
        log_interaction(speech, text)
        
        generate_tts_and_play(r, text, "Sorry for the inconvenience. Have a good day!")
        r.hangup()
    
    return str(r)

@app.route('/reschedule', methods=['POST'])
def reschedule():
    """Handle reschedule confirmation"""
    speech = request.values.get('SpeechResult', '').lower()
    r = VoiceResponse()
    
    log_interaction(speech, "Processing reschedule request")
    
    if is_yes(speech):
        text = "Bahut achha! Aap konse din service reschedule karna chahte hai? Kripya date bataiye."
        
        gather = Gather(
            input='speech',
            action='/reschedule-date',
            speechModel="deepgram_nova-3",
            language='multi',
            timeout=15,
            barge_in=True
        )
        
        generate_tts_for_gather(gather, text, "Which date would you like to reschedule to?")
        r.append(gather)
        
    else:
        text = "Theek hai, current date par hi service hogi. Kya aap koi additional services chahte hai?"
        generate_tts_and_play(r, text, "Alright, service will remain on the current date.")
        r.redirect('/offer-services')
    
    log_interaction(speech, text)
    return str(r)

@app.route('/reschedule-date', methods=['POST'])
def reschedule_date():
    """Handle new service date"""
    new_date_text = request.values.get('SpeechResult', '')
    phone = request.values.get('To', '')
    
    # Extract and parse the date
    extracted_date = extract_dates(new_date_text)
    date_obj = parse_date_string(extracted_date)
    
    # Update database
    user = get_user_data(phone)
    if user and user.get('car_number'):
        update_service_date(user['car_number'], date_obj)
    
    r = VoiceResponse()
    formatted = format_date_for_hindi_speech(date_obj)
    text = f"Perfect! Aapki Bike service {formatted} ko reschedule kar di gayi hai."
    
    log_interaction(new_date_text, text)
    
    generate_tts_and_play(r, text, f"Your service has been rescheduled to {date_obj.strftime('%B %d, %Y')}")
    r.redirect('/offer-services')
    
    return str(r)

@app.route('/offer-services', methods=['POST'])
def offer_services():
    """Offer additional services"""
    r = VoiceResponse()
    
    # Create a more natural service list
    service_list = "Air filter replacement, Oil filter change, Tire rotation, Battery health check, Bike wash, Coolant top-up, Headlight bulb replacement, aur Brake pad inspection"
    
    text = f"Hamare paas kuch additional services bhi available hai jaise: {service_list}. Kya aap koi additional service chahte hai? Service ka naam boliye ya 'nahi' kahiye."
    
    log_interaction("Additional services offer", text)
    
    gather = Gather(
        input='speech',
        action='/handle-services',
        speechModel="deepgram_nova-3",
        language='multi',
        timeout=15,
        barge_in=True
    )
    
    generate_tts_for_gather(gather, text, "Would you like any additional services?")
    r.append(gather)
    
    return str(r)

@app.route('/handle-services', methods=['POST'])
def handle_services():
    """Handle selected additional services"""
    speech = request.values.get('SpeechResult', '').lower()
    phone = request.values.get('To', '')
    
    logger.info(f"[USER SPEECH for services] {speech}")
    
    # Check if user wants no additional services
    if any(word in speech for word in ['nahi', 'nahin', 'no', 'nothing', 'kuch nahi']):
        r = VoiceResponse()
        text = "Theek hai, sirf regular service hi hogi. Dhanyawad!"
        log_interaction(speech, text)
        
        generate_tts_and_play(r, text, "Alright, only regular service then. Thank you!")
        
        # Final message
        final_text = "Aapka service appointment confirm ho gaya hai. Sarthi TVS ko choose karne ke liye dhanyawad!"
        generate_tts_and_play(r, final_text, "Your service appointment is confirmed. Thank you for choosing us!")
        
        r.hangup()
        return str(r)
    
    # Find selected services
    chosen = []
    for i, svc in enumerate(SERVICES, 1):
        # Check by number or service name keywords
        if str(i) in speech or any(word in speech for word in svc.lower().split()):
            if svc not in chosen:
                chosen.append(svc)
    
    r = VoiceResponse()
    
    if chosen:
        services_text = ', '.join(chosen)
        text = f"Bahut badhiya! Aapne ye services select ki hai: {services_text}. Ye sab services add kar di gayi hai."
        
        # Add services to database
        user = get_user_data(phone)
        if user and user.get('car_number'):
            add_selected_services(user['car_number'], chosen)
            
    else:
        text = "Maaf kijiye, main aapki service selection samajh nahi payi. Sirf regular service confirm kar di gayi hai."
    
    log_interaction(speech, text)
    generate_tts_and_play(r, text, "Your selected services have been added.")
    
    # Final thank you message
    final_text = "Aapka service appointment complete confirm ho gaya hai. Sarthi TVS choose karne ke liye bahut bahut dhanyawad! Aapka din shubh ho!"
    generate_tts_and_play(r, final_text, "Your appointment is confirmed. Thank you and have a great day!")
    
    r.hangup()
    return str(r)

# --- Health and Status Endpoints ---

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "time": datetime.utcnow().isoformat(),
        "tts_status": "google_cloud_tts_enabled"
    })

@app.route("/status", methods=["GET", "POST"])
def status():
    """Status endpoint"""
    return jsonify({
        "status": "ok",
        "service": "car_service_agent",
        "version": "1.0"
    })

# --- Error Handlers ---

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

# --- Main ---

if __name__ == "__main__":
    # Ensure audio cache directory exists
    os.makedirs("static/audio_cache", exist_ok=True)
    
    logger.info("Starting Bike Service Agent server on port 5000")
    logger.info(f"TTS Cache directory: static/audio_cache")
    logger.info(f"Request validation: {'Enabled' if VALIDATE_REQUESTS else 'Disabled'}")
    
    app.run(debug=True, host="0.0.0.0", port=5000)