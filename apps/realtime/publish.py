from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

from apps.core.pubsub import publish_event

logger = logging.getLogger(__name__)


def _publish_via_http(channel: str, payload: dict) -> bool:
    base_url = getattr(settings, "REALTIME_PUBLISH_URL", "") or ""
    if not base_url:
        return False
    url = base_url.rstrip("/") + "/internal/publish"
    headers: dict[str, str] = {}
    token = getattr(settings, "REALTIME_PUBLISH_TOKEN", "") or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.post(
            url,
            json={"channel": channel, "payload": payload},
            headers=headers,
            timeout=1.5,
        )
        response.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("realtime publish failed url=%s channel=%s error=%s", url, channel, exc)
        return False


def publish_realtime_event(channel: str, payload: dict[str, Any]) -> None:
    """
    Best-effort publish to realtime service. Falls back to Redis pubsub.
    """
    sent = _publish_via_http(channel, payload)
    if sent:
        return
    publish_event(channel, payload)
