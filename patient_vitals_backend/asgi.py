"""
ASGI config for patient_vitals_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

# asgi.py (in project root, e.g., your_project/asgi.py)
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import patient_vitals_api.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'patient_vitals_backend.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            patient_vitals_api.routing.websocket_urlpatterns
        )
    ),
})
