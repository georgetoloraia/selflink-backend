from __future__ import annotations

from django.conf import settings
from django.urls import re_path


def get_websocket_urlpatterns():
    # Deprecated: Channels-based realtime is opt-in only.
    if not getattr(settings, "REALTIME_CHANNELS_ENABLED", False):
        return []
    from apps.realtime.consumers import RealtimeConsumer

    return [
        re_path(r"^ws/?$", RealtimeConsumer.as_asgi()),
    ]
