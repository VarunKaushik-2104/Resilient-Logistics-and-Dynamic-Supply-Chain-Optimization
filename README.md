🚚 Pred-Logistics AI: Smart Supply Chain Optimizer
Pred-Logistics AI is a real-time logistics management and risk mitigation platform built for the 2026 Google Solution Challenge. It leverages Gemini 2.0 Flash to predict route delays, analyze weather impacts, and provide automated rerouting strategies to ensure supply chain efficiency.

🌟 Key Features
Real-Time Fleet Telemetry: Track the live location of any package on an interactive map. The system uses WebSockets (Socket.IO) to provide second-by-second updates without page refreshes.

Precision ETA & Road Distance: Integration with the Google Maps Distance Matrix API provides accurate road-based distance and a dynamic Estimated Time of Arrival (ETA) that accounts for real-world movement and traffic.

AI-Powered Risk Analysis: Uses Gemini 2.0 Flash to analyze fleet data and provide proactive summaries of high-risk shipments.

Live Route Optimization: If a delay is detected, the AI provides a tactical rerouting strategy for the driver to bypass congestion or weather based on current GPS coordinates.

Omnichannel Alerting: Automated emergency notifications sent via Twilio (WhatsApp) and Gmail (SMTP) when high-risk factors are detected.

Multi-Tenant Security: Secure login system with encrypted credentials allowing different carriers to manage their own private fleets.

🛠️ Tech Stack
Language: Python 3.12

Backend: Flask, Flask-SocketIO (WebSockets)

AI Model: Google Gemini 2.0 Flash (google-genai SDK)

Database: MongoDB Atlas (NoSQL)

APIs: Google Maps (JavaScript & Distance Matrix), OpenWeatherMap, Twilio API

Frontend: HTML5, Tailwind CSS, JavaScript (ES6+)

📡 Technical Implementation: Live Tracking
The project implements a Telemetry Loop to ensure accurate tracking:

The Driver App: Simulates a mobile device sending GPS coordinates to the backend via a secure endpoint.

Flask-SocketIO: The backend receives coordinates and broadcasts them to the distributor’s dashboard in real-time.

Distance Calculation: The system calculates the remaining distance from the live coordinate to the destination using the Haversine formula as a fallback and the Google Maps API for precision road data.

🚀 Getting Started
1. Prerequisites
Python 3.12+

MongoDB Atlas Account

Google Cloud Project (with Gemini & Maps APIs enabled)