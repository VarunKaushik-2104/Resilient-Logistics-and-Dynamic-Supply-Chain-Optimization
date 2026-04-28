import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

print("1. Generating historical delivery data...")
np.random.seed(42) # Keeps the random numbers consistent
n_samples = 1000

# Generate 1000 random deliveries (Distances between 10km and 500km)
distances = np.random.randint(10, 500, n_samples)
# Generate weather (0 = Clear, 1 = Bad Weather)
weathers = np.random.choice([0, 1], n_samples, p=[0.7, 0.3])

# Calculate which deliveries were delayed in the past. 
# Logic: Longer distance + Bad weather = Higher chance of being delayed
delay_probability = (distances / 500) * 0.4 + (weathers * 0.5)
random_factor = np.random.rand(n_samples) * 0.2
delays = (delay_probability + random_factor > 0.6).astype(int)

df = pd.DataFrame({'distance_km': distances, 'weather_bad': weathers, 'is_delayed': delays})

print("2. Training the Random Forest AI...")
# Features (Inputs) and Target (Output)
X = df[['distance_km', 'weather_bad']]
y = df['is_delayed']

# Train the model
model = RandomForestClassifier(n_estimators=50, random_state=42)
model.fit(X, y)

print("3. Saving the trained model...")
# Save the model to a file so Flask can use it
joblib.dump(model, 'delay_model.pkl')
print("✅ Success! Model saved as delay_model.pkl")