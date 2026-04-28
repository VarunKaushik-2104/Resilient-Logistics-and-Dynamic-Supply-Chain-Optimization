import pandas as pd
from pymongo import MongoClient
import math
import random
import os
from dotenv import load_dotenv

# Load the secrets from the .env file
load_dotenv()

# 🔴 MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['logistics_db']
collection = db['shipments']

# Extensive Indian City Coordinates (to cover your uploaded CSV)
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

# Accurate mathematical distance calculation (Haversine Formula)
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Radius of the Earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(R * c)

def process_and_upload_dataset():
    print("🧹 1. Erasing old data from MongoDB...")
    collection.delete_many({}) # THIS IS WHAT WIPES THE OLD DATA

    print("📄 2. Reading india_shipment_data_v2.csv...")
    try:
        df = pd.read_csv('india_shipment_data_v2.csv')
    except FileNotFoundError:
        print("❌ Error: 'india_shipment_data_v2.csv' not found. Please ensure it is in the same folder as seed.py.")
        return

    processed_records = []
    weather_options = ['Clear', 'Clear', 'Clear', 'Heavy Rain', 'Fog', 'Cyclone']
    
    # Process each row in the CSV
    for index, row in df.iterrows():
        # Get data from CSV columns
        origin = str(row.get('Origin', 'Mumbai')).strip()
        destination = str(row.get('Destination', 'Delhi')).strip()
        carrier = str(row.get('Carrier', 'FastFreight')).strip()
        shipment_id = str(row.get('Shipment ID', f"SHP{str(index+1).zfill(4)}")).strip()
        
        # Randomize environmental factors for the simulation
        weather = random.choice(weather_options)
        traffic = round(random.uniform(0.1, 0.95), 2)
        
        # 1. Fetch Coordinates (Defaulting to center of India if city is missing)
        oc = CITY_COORDS.get(origin, {'lat': 20.593, 'lng': 78.962})
        dc = CITY_COORDS.get(destination, {'lat': 20.593, 'lng': 78.962})
        
        # 2. Calculate Accurate Distance
        distance_km = calculate_haversine_distance(oc['lat'], oc['lng'], dc['lat'], dc['lng'])
        
        # 3. Calculate Accurate ETA (Ensuring it always takes at least 1 hour)
        eta_hours = max(1, int(distance_km / 45))
        
        # 4. Simulate real-world progress (Using 0 as the safe minimum bound)
        current_hours = eta_hours + random.randint(1, 12) if weather != 'Clear' else eta_hours - random.randint(0, int(eta_hours*0.5))
        
        # 5. Calculate Risk and Factors based on the real data
        delay_prob = int((traffic * 40) + (30 if weather != 'Clear' else 0) + (15 if current_hours > eta_hours else 0))
        delay_prob = min(max(delay_prob, 5), 98) 
        
        if delay_prob >= 65:
            risk = "HIGH"
        elif delay_prob >= 35:
            risk = "MEDIUM"
        else:
            risk = "LOW"
            
        factors = []
        if weather != 'Clear': factors.append(f"Adverse weather: {weather}")
        if traffic > 0.7: factors.append("Severe route congestion")
        if current_hours > eta_hours: factors.append("Asset currently running behind ETA")

        # Compile the final document
        document = {
            "shipment_id": shipment_id,
            "origin": origin,
            "destination": destination,
            "carrier": carrier,
            "weather": weather,
            "traffic_index": traffic,
            "distance_km": distance_km,
            "eta_hours": eta_hours,
            "current_hours": current_hours,
            "delay_probability": delay_prob,
            "risk_level": risk,
            "delay_factors": factors,
            "origin_lat": oc['lat'],
            "origin_lng": oc['lng'],
            "dest_lat": dc['lat'],
            "dest_lng": dc['lng']
        }
        processed_records.append(document)

    print(f"🚀 3. Uploading {len(processed_records)} clean, calculated shipments to MongoDB...")
    collection.insert_many(processed_records)
    print("✅ Success! The new dataset has replaced the old one.")

if __name__ == "__main__":
    process_and_upload_dataset()