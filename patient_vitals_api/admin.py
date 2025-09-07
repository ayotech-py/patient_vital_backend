from django.contrib import admin
from .models import Patient, Device, Vital, Aggregate

admin.site.register(Patient)
admin.site.register(Device)
admin.site.register(Vital)
admin.site.register(Aggregate)