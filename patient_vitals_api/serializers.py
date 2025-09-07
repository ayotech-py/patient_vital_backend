# serializers.py
from rest_framework import serializers
from .models import Patient, Device, Vital, Aggregate
from django.utils import timezone
from datetime import timedelta

class VitalsUploadSerializer(serializers.Serializer):
    device_id = serializers.CharField(required=True)
    heart_rate = serializers.FloatField(required=False)
    spo2 = serializers.FloatField(required=False)
    temperature = serializers.FloatField(required=False)
    ecg = serializers.FloatField(required=False)
    accel_x = serializers.FloatField(required=False)
    accel_y = serializers.FloatField(required=False)
    accel_z = serializers.FloatField(required=False)
    systolic = serializers.IntegerField(required=False)
    diastolic = serializers.IntegerField(required=False)
    resp = serializers.IntegerField(required=False)
    motion_status = serializers.CharField(max_length=50, required=False)

    def validate(self, data):
        device = Device.objects.filter(device_id=data['device_id']).first()
        if not device:
            raise serializers.ValidationError("Invalid device ID.")
        if not device.assigned_to:
            raise serializers.ValidationError("Device not assigned to any patient.")
        data['patient'] = device.assigned_to
        data['device'] = device
        return data

class VitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vital
        fields = ['timestamp', 'heart_rate', 'spo2', 'temperature', 'ecg_data', 'accel_x', 'accel_y', 'accel_z', 'motion_status']

class AggregateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aggregate
        fields = "__all__"

class PatientDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'
    