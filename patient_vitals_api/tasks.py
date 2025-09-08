from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import numpy as np
import joblib
import neurokit2 as nk
from .models import Patient, Vital, Aggregate
from django.db.models import Avg
import pandas as pd
import os
from openai import OpenAI
from django.utils.timezone import now, timedelta
import openai

@shared_task()
def aggregate_vitals():
    print("Running celery task: aggregate_vitals")
    now = timezone.now()
    five_min_ago = now - timedelta(minutes=5)
    
    for patient in Patient.objects.all():
        recent_vitals = Vital.objects.filter(
            device__assigned_to=patient,
            timestamp__gte=five_min_ago,
            timestamp__lt=now
        ).order_by('timestamp')
        
        if not recent_vitals.exists():
            continue
        
        # Aggregate basic averages
        aggregates = recent_vitals.aggregate(
            avg_heart_rate=Avg('heart_rate'),
            avg_spo2=Avg('spo2'),
            avg_temperature=Avg('temperature'),
            avg_resp=Avg('resp'),
            avg_systolic=Avg('systolic'),
            avg_diastolic=Avg('diastolic'),
            avg_accel_x=Avg('accel_x'),
            avg_accel_y=Avg('accel_y'),
            avg_accel_z=Avg('accel_z')
        )

        
        # Collect all ECG data for HRV
        ecg_data_all = []
        for vital in recent_vitals:
            if vital.ecg:
                ecg_data_all.append(vital.ecg)
        
        hrv_value = None
        try:
            if ecg_data_all:
                signals, info = nk.ecg_process(ecg_data_all, sampling_rate=100)  # Adjust sampling_rate
                r_peaks = info['ECG_R_Peaks']
                if len(r_peaks) > 1:
                    hrv = nk.hrv(r_peaks, sampling_rate=100, show=False)
                    hrv_value = hrv['HRV_RMSSD'][0]  # RMSSD in ms
        except Exception as e:
            print(f"Error computing HRV for patient {patient.id}: {e}")
        # Fallback HRV from heart_rate (rough estimate)
        if not hrv_value and recent_vitals.count() > 1:
            heart_rates = [v.heart_rate for v in recent_vitals if v.heart_rate]
            if len(heart_rates) > 1:
                diff = np.diff(heart_rates)
                hrv_value = np.std(diff) * 1000 / 5
        

        bmi = patient.weight / (patient.height ** 2)
        vital_map = (aggregates['avg_systolic'] + 2 * aggregates['avg_diastolic']) / 3
        dpp = aggregates['avg_systolic'] - aggregates['avg_diastolic']

        gender_map = {'male': 0, 'female': 1}
        gender_encoded = gender_map.get(patient.gender.lower(), 0)

        features = {
            'Heart Rate': aggregates['avg_heart_rate'] or 0,
            'Respiratory Rate': aggregates['avg_resp'] or 0,
            'Body Temperature': aggregates['avg_temperature'] or 0,
            'Oxygen Saturation': aggregates['avg_spo2'] or 0,
            'Systolic Blood Pressure': aggregates['avg_systolic'] or 0,
            'Diastolic Blood Pressure': aggregates['avg_diastolic'] or 0,
            'Age': patient.age,
            'Gender': gender_encoded,
            'Weight (kg)': patient.weight,
            'Height (m)': patient.height,
            'Derived_HRV': hrv_value,
            'Derived_Pulse_Pressure': dpp,
            'Derived_BMI': bmi,
            'Derived_MAP': vital_map,
        }

        risk_level, confidence = predict_risk(features=features)
        
        # Generate summary
        summary = generate_summary_for_patient(patient, risk_level)
        
        # Save to Aggregate
        Aggregate.objects.create(
            patient=patient,
            start_time=five_min_ago,
            end_time=now,
            avg_heart_rate=aggregates['avg_heart_rate'],
            avg_spo2=aggregates['avg_spo2'],
            avg_temperature=aggregates['avg_temperature'],
            avg_accel_x=aggregates['avg_accel_x'],
            avg_accel_y=aggregates['avg_accel_y'],
            avg_accel_z=aggregates['avg_accel_z'],
            risk_level=risk_level,
            confidence=confidence,
            summary=summary
        )

def predict_risk(features):
    model_path = 'patient_vitals_api/ml_model/xgboost_model_without_original_risk.pkl'
    scaler_path = 'patient_vitals_api/ml_model/scaler_without_original_risk.pkl'

    risk_model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    feature_columns = [
        'Heart Rate',
        'Respiratory Rate',
        'Body Temperature',
        'Oxygen Saturation',
        'Systolic Blood Pressure',
        'Diastolic Blood Pressure',
        'Age',
        'Gender',
        'Weight (kg)',
        'Height (m)',
        'Derived_HRV',
        'Derived_Pulse_Pressure',
        'Derived_BMI',
        'Derived_MAP',
    ]

    input_df = pd.DataFrame([features])

    input_df = input_df[feature_columns]

    input_scaled = scaler.transform(input_df)

    risk_mapping = {0: 'Low', 1: 'Moderate', 2: 'High'}
    
    prediction = risk_model.predict(input_scaled)[0]
    confidence = None
    if hasattr(risk_model, 'predict_proba'):
        # Get the probability for the predicted class
        confidence = risk_model.predict_proba(input_scaled)[0][prediction]
    print("The model output: ", prediction, confidence)
    return risk_mapping.get(prediction, 'Unknown'), confidence


def generate_summary_for_patient(patient, risk_level):
    minute = None
    if risk_level == 'High':
        minute = 15
    elif risk_level == "Moderate":
        minute = 10
    else:
        minute = 5

    now_time = now()
    start_time = now_time - timedelta(minutes=minute)
    
    readings = Vital.objects.filter(
        patient=patient, 
        timestamp__gte=start_time
    ).order_by('timestamp')

    if len(readings) < 2:
        return  # Not enough data to compute trends

    # Compute differences
    hr_change = readings.last().heart_rate - readings.first().heart_rate
    sys_change = readings.last().systolic - readings.first().systolic
    dia_change = readings.last().diastolic - readings.first().diastolic
    spo2_change = readings.last().spo2 - readings.first().spo2
    temp_change = readings.last().temperature - readings.first().temperature

    # Create trend string
    trend = f"""
    The patient's vital sign changes over the last {minute} minutes are:
    - Heart Rate: {readings.first().heart_rate} → {readings.last().heart_rate} ({hr_change:+.1f})
    - Systolic BP: {readings.first().systolic} → {readings.last().systolic} ({sys_change:+.1f})
    - Diastolic BP: {readings.first().diastolic} → {readings.last().diastolic} ({dia_change:+.1f})
    - SpO₂: {readings.first().spo2} → {readings.last().spo2} ({spo2_change:+.1f})
    - Temperature: {readings.first().temperature}°C → {readings.last().temperature}°C ({temp_change:+.1f})
    """

    # Add patient bio
    bio = f"Patient is a {patient.age}-year-old {patient.gender.lower()} weighing {patient.weight}kg and {patient.height}m tall."

    # Final prompt
    full_prompt = f"""
    {bio}

    Based on the following vital signs trend, give a concise medical-style summary of the patient's current condition and advice for next steps. Be professional and informative.

    {trend}
    """

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": (
                "You are a medical assistant. Write a brief, straight-to-the-point summary of patient vitals in the form of a single paragraph. "
                "Focus only on changes and trends over the last period of time. "
                "Avoid bullet points or lists and keep the response concise. The word count should be under 30 words."
            )},
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=100,
        temperature=0.5
    )

    summary_text = response.choices[0].message.content.strip()

    return summary_text