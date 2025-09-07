# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import VitalsUploadSerializer, PatientDataSerializer, AggregateSerializer
from .models import Patient, Vital, Device, Aggregate
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import redis
import joblib
import random

# Optional: Redis connection (configure as per your setup)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)  # Adjust credentials

class VitalsUploadView(APIView):
    def post(self, request):
        serializer = VitalsUploadSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            validated_data.pop('patient')
            device_id = validated_data.pop('device_id')


            device = Device.objects.get(device_id=device_id)
            patient = device.assigned_to
            validated_data.pop('device')
            
            # Save to Vital
            vitals = Vital.objects.create(
                device=device,
                patient=patient,
                **validated_data
            )
             
            # Update Redis cache for recent series (example for heart_rate and ecg)
            patient_id_str = str(patient.id)
            confidence = 0
            risk_level = "N/A"
            summary = ""
            
            patient_vitals = Vital.objects.filter(patient=patient).order_by("-id")
            hr_data = patient_vitals.values_list('heart_rate', flat=True)[:20]
            spo2_data = patient_vitals.values_list('spo2', flat=True)[:20]
            ecg_data = patient_vitals.values_list('ecg', flat=True)[:200]

            aggregates = Aggregate.objects.filter(patient=patient)
            if aggregates.exists():     
                aggregates = aggregates.order_by('-id')[:100]
                confidence = aggregates.first().confidence * 100
                risk_level = aggregates.first().risk_level
                summary = aggregates.first().summary
            
            # Broadcast via WebSockets (assuming Channels set up)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'patient_{patient_id_str}',
                {
                    'type': 'vitals.update',
                    'data': {
                        "confidence":  confidence,
                        "risk_level": risk_level,
                        "summary": summary,
                        "hr_data": list(hr_data),
                        "spo2_data": list(spo2_data),
                        "ecg_data": list(ecg_data),
                        "aggregates": AggregateSerializer(aggregates, many=True).data,
                        **dict(PatientDataSerializer(patient).data),
                        **dict(VitalsUploadSerializer(vitals).data)
                    }
                }
            )
            
            return Response({'status': 'success', 'message': 'Vitals uploaded successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PatientDataView(APIView):
    def get(self, request):
        patient = Patient.objects.all()
        
        serializer = PatientDataSerializer(patient, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)