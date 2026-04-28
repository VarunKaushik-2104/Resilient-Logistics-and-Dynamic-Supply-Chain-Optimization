import requests
import time

# 🔴 Make sure you register an account with this EXACT company name in your login screen, 
# and ensure a shipment with this ID exists for that company in your MongoDB.
COMPANY = "FastFreight" 
SHIPMENT_ID = "SHP0001" 

# Simulating a truck driving north on a highway (latitudes increasing)
gps_path = [
    {"lat": 19.5, "lng": 73.0},
    {"lat": 19.8, "lng": 73.2},
    {"lat": 20.1, "lng": 73.4},
    {"lat": 20.5, "lng": 73.6},
    {"lat": 21.0, "lng": 73.8}
]

print(f"Starting simulated drive for {SHIPMENT_ID}...")

for coords in gps_path:
    payload = {
        "company": COMPANY,
        "shipment_id": SHIPMENT_ID,
        "lat": coords["lat"],
        "lng": coords["lng"]
    }
    
    # Ping the Webhook
    requests.post("http://127.0.0.1:8000/api/telemetry", json=payload)
    print(f"📍 Pinged Location: {coords['lat']}, {coords['lng']}")
    
    # Wait 3 seconds before moving the truck again
    time.sleep(3)

print("Truck arrived.")