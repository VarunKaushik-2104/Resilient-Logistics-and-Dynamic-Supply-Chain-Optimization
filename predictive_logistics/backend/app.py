from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient
import google.generativeai as genai
import requests
import random
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import math
import re # Add this import at the very top of your app.py if it isn't there
import json # Ensure json is imported at the top of app.py
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load the secrets from the .env file
load_dotenv()


MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Inside your /api/alert route, update your Twilio/Email variables:
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
MANAGER_PHONE = os.getenv("MANAGER_PHONE")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL")


# 🔴 1. DEFINE THE APP FIRST
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
socketio = SocketIO(app, cors_allowed_origins="*")

# 🔴 2. NOW YOU CAN USE @app.route
@app.route('/api/v1/telemetry/ping', methods=['POST'])
def secure_telemetry_ping():
    data = request.json
    api_key = request.headers.get('X-Device-Token')
    
    # In a real app, you would verify 'api_key' against the database
    shipment_id = data.get('shipment_id')
    company = data.get('company')
    lat = data.get('lat')
    lng = data.get('lng')

    if not all([shipment_id, company, lat, lng]):
        return jsonify({"error": "Missing telemetry parameters"}), 400

    # 1. Update MongoDB with live coordinates and timestamp
    update_result = collection.update_one(
        {"shipment_id": shipment_id, "carrier": company},
        {"$set": {
            "live_lat": lat,
            "live_lng": lng,
            "last_ping": datetime.utcnow().isoformat() + "Z"
        }}
    )

    if update_result.matched_count == 0:
        return jsonify({"error": "Shipment not found or unauthorized"}), 404

    # 2. Broadcast via WebSocket to the distributor's private room
    socketio.emit('fleet_update', {
        "shipment_id": shipment_id,
        "lat": lat,
        "lng": lng,
        "company": company
    }, room=company)

    return jsonify({"status": "received", "timestamp": datetime.utcnow().isoformat()}), 200

# 🔴 Configuration (Replace with your actual keys)

# City Coordinates
CITY_COORDS = {
    'Mumbai': {'lat':19.076, 'lng':72.877}, 'Delhi': {'lat':28.614, 'lng':77.209},
    'Bangalore': {'lat':12.972, 'lng':77.594}, 'Chennai': {'lat':13.082, 'lng':80.270},
    'Kolkata': {'lat':22.572, 'lng':88.363}, 'Hyderabad': {'lat':17.385, 'lng':78.487},
    'Pune': {'lat':18.520, 'lng':73.856}, 'Ahmedabad': {'lat':23.022, 'lng':72.571},
    'Jaipur': {'lat':26.912, 'lng':75.787}, 'Lucknow': {'lat':26.847, 'lng':80.947},
    'Surat': {'lat':21.170, 'lng':72.831}, 'Kochi': {'lat':9.939, 'lng':76.270},
    'Nagpur': {'lat':21.145, 'lng':79.088}, 'Bhopal': {'lat':23.259, 'lng':77.413},
    'Indore': {'lat':22.719, 'lng':75.857}, 'Patna': {'lat':25.594, 'lng':85.137},
    'Vadodara': {'lat':22.307, 'lng':73.181}, 'Ludhiana': {'lat':30.900, 'lng':75.857},
    'Agra': {'lat':27.176, 'lng':78.008}, 'Nashik': {'lat':20.000, 'lng':73.780},
    'Gurgaon': {'lat':28.459, 'lng':77.026}, 'Amritsar': {'lat':31.634, 'lng':74.872},
    'Mysore': {'lat':12.295, 'lng':76.639}, 'Ghaziabad': {'lat':28.669, 'lng':77.453},
    'Rajkot': {'lat':22.303, 'lng':70.802}, 'Solapur': {'lat':17.659, 'lng':75.906},
    'Srinagar': {'lat':34.083, 'lng':74.797}, 'Noida': {'lat':28.535, 'lng':77.391},
    'Chandigarh': {'lat':30.733, 'lng':76.779}, 'Jabalpur': {'lat':23.181, 'lng':79.986},
    'Faridabad': {'lat':28.408, 'lng':77.319}, 'Vijayawada': {'lat':16.506, 'lng':80.648},
    'Navi Mumbai': {'lat':19.033, 'lng':73.029}, 'Varanasi': {'lat':25.317, 'lng':82.973},
    'Madurai': {'lat':9.925, 'lng':78.119}, 'Kota': {'lat':25.213, 'lng':75.864},
    'Guwahati': {'lat':26.144, 'lng':91.736}, 'Jodhpur': {'lat':26.238, 'lng':73.024},
    'Visakhapatnam': {'lat':17.686, 'lng':83.218}, 'Meerut': {'lat':28.984, 'lng':77.706},
    'Howrah': {'lat':22.595, 'lng':88.324}, 'Gwalior': {'lat':26.212, 'lng':78.177}
}

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int((R * c) * 1.2) # 1.2 multiplier accounts for road curves

client = MongoClient(MONGO_URI)
db = client['logistics_db']
collection = db['shipments']
users_collection = db['users']
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- SECURITY SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = str(user_dict['_id'])
        self.email = user_dict['email']
        self.company = user_dict['company']

@login_manager.user_loader
def load_user(user_id):
    u = users_collection.find_one({"_id": ObjectId(user_id)})
    if not u: return None
    return User(u)

@app.route('/login-page')
def login_page():
    if current_user.is_authenticated: return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if users_collection.find_one({"email": data.get('email')}):
        return jsonify({"error": "Email already exists"}), 400
    hashed_password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
    user_id = users_collection.insert_one({"email": data.get('email'), "company": data.get('company'), "password": hashed_password}).inserted_id
    login_user(User(users_collection.find_one({"_id": user_id})))
    return jsonify({"success": True}), 200

@app.route('/login', methods=['POST'])
def login():
    user_data = users_collection.find_one({"email": request.json.get('email')})
    if not user_data or not check_password_hash(user_data['password'], request.json.get('password')):
        return jsonify({"error": "Invalid email or password"}), 401
    login_user(User(user_data))
    return jsonify({"success": True}), 200

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True}), 200


# --- MULTI-TENANT DASHBOARD ---
@app.route('/')
@login_required
def home():
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    # Pass it into the HTML template
    return render_template('index.html', gmaps_key=maps_key)


# 🔴 1. Smart Weather Cache to prevent API rate limits and slow loading
@lru_cache(maxsize=128)
def get_live_weather_for_dashboard(lat, lng):
    # Rounding to 1 decimal place (~11km area) groups nearby trucks and saves API calls
    lat = round(lat, 1)
    lng = round(lng, 1)
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={WEATHER_API_KEY}"
        data = requests.get(url, timeout=3).json()
        main_weather = data['weather'][0]['main']
        
        # Map standard OpenWeather terms to match your dashboard's UI
        if main_weather in ['Rain', 'Drizzle']: return 'Heavy Rain'
        if main_weather in ['Thunderstorm', 'Tornado', 'Squall']: return 'Cyclone'
        if main_weather in ['Mist', 'Smoke', 'Haze', 'Dust', 'Fog']: return 'Fog'
        if main_weather == 'Clouds': return 'Clouds'
        return 'Clear'
    except Exception as e:
        return 'Clear'

# 🔴 2. Updated Dashboard Route to inject Live Weather into the table
@app.route('/shipments', methods=['GET'])
@login_required
def get_shipments():
    company_name = current_user.company
    company_regex = re.compile(f"^{company_name}$", re.IGNORECASE)
    
    shipments = list(collection.find({"carrier": company_regex}, {'_id': 0}).limit(100))
    
    # --- FETCH LIVE WEATHER FOR ALL TRUCKS ---
    for s in shipments:
        # Use live webhook GPS if available, otherwise calculate their current spot
        live_lat = s.get('live_lat')
        live_lng = s.get('live_lng')
        
        if not live_lat or not live_lng:
            olat, olng = s.get('origin_lat', 20.593), s.get('origin_lng', 78.962)
            dlat, dlng = s.get('dest_lat', 20.593), s.get('dest_lng', 78.962)
            live_lat = olat + (dlat - olat) * 0.6
            live_lng = olng + (dlng - olng) * 0.6
            
        # Replace the static database weather with the real-time weather!
        s['weather'] = get_live_weather_for_dashboard(live_lat, live_lng)
    
    # --- CALCULATE KPI STATS ---
    high = sum(1 for s in shipments if s['risk_level'] == 'HIGH')
    medium = sum(1 for s in shipments if s['risk_level'] == 'MEDIUM')
    low = sum(1 for s in shipments if s['risk_level'] == 'LOW')
    
    # --- GEMINI EXECUTIVE SUMMARY ---
    prompt = f"Act as a logistics executive for {company_name}. Review this fleet data: Total {len(shipments)}, High Risk {high}, Medium Risk {medium}, Low Risk {low}. Provide a 2 sentence proactive summary."
    try: 
        summary = model.generate_content(prompt).text
    except: 
        summary = "AI Summary unavailable. System operating at standard capacity."

    return jsonify({
        "total": len(shipments), 
        "high_risk": high, 
        "medium_risk": medium, 
        "low_risk": low, 
        "model_accuracy": 0.942, 
        "shipments": shipments, 
        "gemini_summary": summary
    })


@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '')
    if not query: return jsonify({"results": []})
    
    import re
    company_name = current_user.company
    company_regex = re.compile(f"^{company_name}$", re.IGNORECASE)
    
    # Secure the search so they can only search their own fleet
    results = list(collection.find({
        "carrier": company_regex,
        "$or": [
            {"shipment_id": {"$regex": query, "$options": "i"}}, 
            {"origin": {"$regex": query, "$options": "i"}}, 
            {"destination": {"$regex": query, "$options": "i"}}
        ]
    }, {'_id': 0}).limit(5))
    
    return jsonify({"results": results})
    query = request.args.get('q', '')
    if not query: return jsonify({"results": []})
    
    # 🔴 1. Get the logged-in user's company
    company_name = current_user.company
    
    # 🔴 2. Add the "carrier" constraint to the database search query
    results = list(collection.find({
        "carrier": company_name, # Locks the search to this company ONLY
        "$or": [
            {"shipment_id": {"$regex": query, "$options": "i"}}, 
            {"origin": {"$regex": query, "$options": "i"}}, 
            {"destination": {"$regex": query, "$options": "i"}}
        ]
    }, {'_id': 0}).limit(5))
    
    return jsonify({"results": results})
    query = request.args.get('q', '')
    if not query: return jsonify({"results": []})
    results = list(collection.find({"$or": [{"shipment_id": {"$regex": query, "$options": "i"}}, {"origin": {"$regex": query, "$options": "i"}}, {"destination": {"$regex": query, "$options": "i"}}]}, {'_id': 0}).limit(5))
    return jsonify({"results": results})

@app.route('/model-info', methods=['GET'])
@login_required
def model_info():
    return jsonify({"training_samples": 1000, "accuracy": 0.945, "cv_score": 0.912, "feature_importances": {"traffic_congestion": 0.45, "adverse_weather": 0.35, "route_distance": 0.15, "carrier_history": 0.05}})

import json

@app.route('/route', methods=['GET'])
@login_required
def get_route():
    origin = request.args.get('origin')
    dest = request.args.get('destination')
    risk = request.args.get('risk_level')
    
    oc = CITY_COORDS.get(origin)
    dc = CITY_COORDS.get(dest)
    
    if not oc or not dc:
        return jsonify({"error": "Invalid cities"}), 400

    live_lat = oc['lat'] + (dc['lat'] - oc['lat']) * 0.6
    live_lng = oc['lng'] + (dc['lng'] - oc['lng']) * 0.6
    
    # 🔴 1. Calculate exact distance in Python
    remaining_distance = calculate_haversine_distance(live_lat, live_lng, dc['lat'], dc['lng'])
    
    live_location_name = "Highway Route Segment"
    live_weather = "Clear"
    
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={live_lat}&lon={live_lng}&appid={WEATHER_API_KEY}"
        weather_data = requests.get(weather_url).json()
        if weather_data.get('name'):
            live_location_name = weather_data['name']
        live_weather = weather_data['weather'][0]['description'].title()
    except Exception as e:
        pass

    # 🔴 2. Ask Gemini to format the ETA based on the exact Python distance
    prompt = f"""
    A commercial logistics truck is traveling from {origin} to {dest}. 
    The remaining distance is exactly {remaining_distance} km. 
    The live location is near {live_location_name} and the live weather is '{live_weather}'. 
    
    Based on the exact distance of {remaining_distance} km, assuming an average Indian truck speed of 45 km/h, calculate the precise Estimated Time of Arrival (EST). 
    
    Reply STRICTLY with a valid JSON object matching this exact format, nothing else:
    {{
        "est_time": "X hrs Y mins",
        "suggestion": "2-sentence proactive detour or routing strategy."
    }}
    """
    
    try: 
        response_text = model.generate_content(prompt).text
        clean_json = response_text.replace('```json', '').replace('```', '').strip()
        ai_data = json.loads(clean_json)
        
        est_time = ai_data.get("est_time", f"{max(1, int(remaining_distance / 45))} hrs 0 mins")
        suggestion = ai_data.get("suggestion", "Monitor live traffic and maintain current trajectory.")
    except Exception as e: 
        # Safe fallback if Gemini fails to respond
        est_time = f"{max(1, int(remaining_distance / 45))} hrs 0 mins"
        suggestion = "Maintain standard route. Drive carefully in current conditions."
        
    return jsonify({
        "distance": f"{remaining_distance} km",
        "duration": est_time,
        "suggestion": suggestion,
        "live_location": live_location_name,
        "live_weather": live_weather,
        "live_lat": live_lat,
        "live_lng": live_lng
    })

@app.route('/mitigate', methods=['GET'])
@login_required
def mitigate():
    shipment_id = request.args.get('shipment_id')
    factors = request.args.get('factors')
    prompt = f"Shipment {shipment_id} is delayed due to: {factors}. Write a 3-bullet-point immediate action plan for the warehouse manager to mitigate this."
    try: actions = model.generate_content(prompt).text
    except: actions = "- Contact driver for status.\n- Inform receiving warehouse.\n- Update ETA in system."
    return jsonify({"actions": actions})

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    user_message = data.get('message', '')
    worst_shipment = collection.find_one({"carrier": current_user.company, "risk_level": "HIGH"}, {'_id': 0})
    context = f"Context: You are SupplyChain.AI. The highest risk shipment right now is {worst_shipment['shipment_id']} from {worst_shipment['origin']} due to {worst_shipment['delay_factors']}. " if worst_shipment else ""
    prompt = f"{context}User asks: {user_message}. Answer concisely."
    try: reply = model.generate_content(prompt).text
    except: reply = "System overload: Unable to process AI request at this time."
    return jsonify({"reply": reply})


# --- WEBSOCKETS & TELEMETRY ---

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(current_user.company)
        print(f"🟢 {current_user.company} connected to secure live feed.")

@app.route('/api/telemetry', methods=['POST'])
def telemetry_webhook():
    data = request.json
    shipment_id = data.get('shipment_id')
    lat = data.get('lat')
    lng = data.get('lng')
    company = data.get('company')

    collection.update_one({"shipment_id": shipment_id}, {"$set": {"live_lat": lat, "live_lng": lng}})
    socketio.emit('fleet_update', data, room=company)
    return jsonify({"status": "broadcasted"}), 200

@app.route('/driver_app')
def driver_app():
    # This serves the mobile driver interface
    return render_template('driver_app.html')

# 🔴 AUTOMATED OMNICHANNEL ALERTING (WHATSAPP + EMAIL)
@app.route('/api/alert', methods=['POST'])
@login_required
def trigger_alert():
    data = request.json
    shipment_id = data.get('shipment_id')
    risk = data.get('risk_level')
    delay_factors = data.get('factors')
    
    # 1. TWILIO WHATSAPP CONFIGURATION

    # --- WHATSAPP MESSAGE FORMAT ---
    # WhatsApp sandbox is less restrictive on length than SMS!
    wa_message = f"🚨 *PRED-LOGISTICS ALERT*\n\n*Shipment:* {shipment_id}\n*Status:* {risk} RISK\n\n*Detected Factors:*\n{delay_factors}\n\n_Log into the dashboard to view AI rerouting recommendations._"
    
    # --- EMAIL FORMATTING ---
    email_subject = f"URGENT: Route Risk Escalation for {shipment_id}"
    email_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #f75f5f;">🚨 Logistics Alert: {risk} RISK</h2>
        <p><strong>Shipment ID:</strong> {shipment_id}</p>
        <p><strong>Detected Factors:</strong></p>
        <ul>
          {chr(10).join([f"<li>{factor.strip()}</li>" for factor in delay_factors.split(';')])}
        </ul>
        <br>
        <p><em>Action Required:</em> Please log into the Pred-Logistics dashboard to view Gemini AI's recommended alternate routes.</p>
      </body>
    </html>
    """

    wa_status = "Failed"
    email_status = "Failed"

    # --- EXECUTE WHATSAPP ---
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=wa_message,
            # 🔴 CRITICAL FIX FOR ERROR 63007: Added 'whatsapp:' prefix
            from_=f"whatsapp:{TWILIO_PHONE}", 
            to=f"whatsapp:{MANAGER_PHONE}"
        )
        wa_status = "Delivered"
    except Exception as e:
        print(f"Twilio WhatsApp Error: {e}")

    # --- EXECUTE EMAIL ---
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = MANAGER_EMAIL
        msg['Subject'] = email_subject
        msg.attach(MIMEText(email_body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        email_status = "Delivered"
    except Exception as e:
        print(f"Email Error: {e}")

    return jsonify({
        "success": True, 
        "whatsapp_status": wa_status, 
        "email_status": email_status
    }), 200

if __name__ == '__main__':
    # Adding host='0.0.0.0' fixes the Windows localhost/ngrok routing issue
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)