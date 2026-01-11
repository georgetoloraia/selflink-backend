from __future__ import annotations

import logging

from django.conf import settings
from django.urls import re_path


logger = logging.getLogger(__name__)


def get_websocket_urlpatterns():
    # Deprecated: Channels-based realtime is opt-in only.
    if not getattr(settings, "REALTIME_CHANNELS_ENABLED", False):
        return []
    logger.warning(
        "Django Channels realtime is deprecated. "
        "Use the FastAPI realtime gateway (ws://localhost:8002/ws) instead."
    )
    from apps.realtime.consumers import RealtimeConsumer

    return [
        re_path(r"^ws/?$", RealtimeConsumer.as_asgi()),
    ]
