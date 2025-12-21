from __future__ import annotations

from django.urls import re_path

from apps.realtime.consumers import RealtimeConsumer

websocket_urlpatterns = [
    re_path(r"^ws/?$", RealtimeConsumer.as_asgi()),
]
