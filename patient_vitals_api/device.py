import requests
import time
import random
import json

# Endpoint URL - replace with your actual URL, e.g., 'http://localhost:8000/api/vitals/upload/' or deployed URL
URL = 'http://127.0.0.1:8000/api/vitals/upload/'  # Change this

# Assume a valid device_id exists in your DB, e.g., from Device model
DEVICE_ID = 'ESP01'  # Replace with a real device_id, like 'ESP32-123456'

# Headers if needed, e.g., for auth; add API key if secured
HEADERS = {
    'Content-Type': 'application/json',
    # 'Authorization': 'Bearer your_token'  # If using auth
}

def generate_sample_payload():
    # Generate realistic sample data mimicking the device
    # Heart rate: 60-100 BPM
    heart_rate = random.uniform(60, 100)
    
    # SpO2: 95-100%
    spo2 = random.uniform(95, 100)
    
    # Temperature: 97-99 °F
    temperature = random.uniform(97, 99)
    
    ecg = random.uniform(-0.2, 0.2)
    
    # Accelerometer: Typical values, e.g., around 0 for x/y, 9.8 for z (gravity)
    accel_x = random.uniform(-1, 1)
    accel_y = random.uniform(-1, 1)
    accel_z = random.uniform(9, 10)

    systolic = random.uniform(110, 130)
    diastolic = random.uniform(70, 85)
    resp = random.uniform(16, 20)
    
    # Motion status: Random choice
    motion_status = random.choice(['Normal Activity', 'Low Activity', 'High Activity'])
    
    return {
        'device_id': DEVICE_ID,
        'heart_rate': heart_rate,
        'spo2': spo2,
        'temperature': temperature,
        'ecg': ecg,
        'accel_x': accel_x,
        'accel_y': accel_y,
        'accel_z': accel_z,
        'systolic': int(systolic),
        'diastolic': int(diastolic),
        'resp': int(resp),
        'motion_status': motion_status
    }

def send_payload():
    payload = generate_sample_payload()
    try:
        response = requests.post(URL, headers=HEADERS, data=json.dumps(payload))
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending payload: {e}")

# Mimic device sending every 5 seconds (run indefinitely)
while True:
    send_payload()
    time.sleep(2)