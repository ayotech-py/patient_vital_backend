from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField

class Patient(models.Model):
    
    patient_id = models.CharField(max_length=20, unique=True, help_text="Unique patient ID, e.g., PT-2024-001")
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    room = models.CharField(max_length=50, help_text="Room number, e.g., ICU-12")
    weight = models.FloatField(help_text="Weight in kilogram")
    height = models.FloatField(help_text="Height in metres")
    
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    gender = models.CharField(choices=GENDER_CHOICES, help_text="Gender: Male or Female")
    
    condition = models.TextField(help_text="Patient's medical condition or monitoring reason")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.patient_id})"

class Device(models.Model):
    device_id = models.CharField(max_length=50, unique=True, help_text="ESP32 device ID or MAC address")
    assigned_to = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices")
    active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.device_id

class Vital(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="vitals")
    heart_rate = models.IntegerField(null=True, blank=True, help_text="Heart rate in BPM")
    spo2 = models.IntegerField(null=True, blank=True, help_text="SpO2 percentage")
    temperature = models.FloatField(null=True, blank=True, help_text="Body temperature in °F")
    ecg = models.FloatField(null=True, blank=True, help_text="ECG waveform samples")
    accel_x = models.FloatField(null=True, blank=True)
    accel_y = models.FloatField(null=True, blank=True)
    accel_z = models.FloatField(null=True, blank=True)
    systolic = models.IntegerField(null=True, blank=True)
    diastolic = models.IntegerField(null=True, blank=True)
    resp = models.IntegerField(null=True, blank=True)
    motion_status = models.CharField(max_length=50, null=True, blank=True, help_text="e.g., 'Normal Activity'")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Vital for {self.device} at {self.timestamp}"

class Aggregate(models.Model):
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
    ]

    start_time = models.DateTimeField(help_text="Start of the aggregation period")
    end_time = models.DateTimeField(help_text="End of the aggregation period")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="aggregates")
    avg_heart_rate = models.FloatField(null=True, blank=True)
    avg_spo2 = models.FloatField(null=True, blank=True)
    avg_temperature = models.FloatField(null=True, blank=True)
    avg_accel_x = models.FloatField(null=True, blank=True)
    avg_accel_y = models.FloatField(null=True, blank=True)
    avg_accel_z = models.FloatField(null=True, blank=True)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='N/A')
    confidence = models.FloatField(null=True, blank=True, help_text="ML confidence score, e.g., 0.94", default=0)
    summary = models.TextField(help_text="LLM-generated summary")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Aggregate for {self.patient} from {self.start_time} to {self.end_time}"