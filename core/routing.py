from __future__ import annotations

from django.urls import re_path


def get_websocket_urlpatterns():
    from apps.realtime.consumers import RealtimeConsumer

    return [
        re_path(r"^ws/?$", RealtimeConsumer.as_asgi()),
    ]
