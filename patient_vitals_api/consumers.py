# consumers.py (in your app directory)
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class PatientConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.patient_id = self.scope['url_route']['kwargs']['patient_id']
        self.group_name = f'patient_{self.patient_id}'
        
        # Optional: Check if patient exists and user has permission
        if not await self.patient_exists():
            await self.close()
            return
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to patient vitals'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Handle messages from group (e.g., vitals.update from view)
    async def vitals_update(self, event):
        data = event['data']
        await self.send(text_data=json.dumps({
            'type': 'vitals_update',
            'data': data
        }))

    # Helper to check patient
    @database_sync_to_async
    def patient_exists(self):
        from .models import Patient
        return Patient.objects.filter(id=self.patient_id).exists()