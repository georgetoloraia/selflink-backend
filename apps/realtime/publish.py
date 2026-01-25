from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

from apps.core.pubsub import publish_event

logger = logging.getLogger(__name__)


def _publish_via_http(channel: str, payload: dict) -> tuple[bool, str | None]:
    base_url = getattr(settings, "REALTIME_PUBLISH_URL", "") or ""
    if not base_url:
        return False, "no_publish_url"
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
            timeout=(0.5, 1.0),
        )
        if response.ok:
            return True, None
        return False, f"http_{response.status_code}"
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("realtime publish failed url=%s channel=%s error=%s", url, channel, exc)
        return False, str(exc)


def publish_realtime_event(channel: str, payload: dict[str, Any], *, context: dict | None = None) -> None:
    """
    Best-effort publish to realtime service. Falls back to Redis pubsub.
    """
    extra = {"channel": channel, "event_type": payload.get("type")}
    if context:
        extra.update(context)
    logger.info("gift_realtime.publish_attempt", extra=extra)
    sent, error = _publish_via_http(channel, payload)
    if sent:
        logger.info("gift_realtime.publish_success", extra={**extra, "path": "http"})
        return
    if error:
        logger.warning("gift_realtime.publish_failure", extra={**extra, "path": "http", "error": error})
    logger.info("gift_realtime.publish_fallback_redis", extra=extra)
    ok = publish_event(channel, payload)
    if ok:
        logger.info("gift_realtime.publish_success", extra={**extra, "path": "redis"})
    else:
        logger.warning("gift_realtime.publish_failure", extra={**extra, "path": "redis"})
