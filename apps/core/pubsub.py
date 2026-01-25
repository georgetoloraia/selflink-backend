from __future__ import annotations

import json
import logging
from functools import lru_cache

from django.conf import settings
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    url = getattr(settings, "PUBSUB_REDIS_URL", "redis://redis:6379/1")
    return Redis.from_url(url)


def publish_event(channel: str, payload: dict) -> bool:
    try:
        client = get_redis_client()
        client.publish(channel, json.dumps(payload))
        return True
    except RedisError as exc:  # pragma: no cover - log and continue
        logger.warning("Failed to publish event on %s: %s", channel, exc)
        return False


def publish_events(channels: list[str], payload: dict) -> None:
    for channel in channels:
        publish_event(channel, payload)
