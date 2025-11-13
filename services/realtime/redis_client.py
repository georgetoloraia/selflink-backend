from __future__ import annotations

import json
from functools import lru_cache
import logging

from redis.asyncio import Redis
from fastapi.encoders import jsonable_encoder

from .config import settings

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_async_redis() -> Redis:
    return Redis.from_url(settings.redis_url)


async def publish(channel: str, payload: dict) -> None:
    redis = get_async_redis()
    try:
        encoded = json.dumps(jsonable_encoder(payload))
    except (TypeError, ValueError) as exc:
        logger.warning("Realtime publish serialization failed for channel %s: %s", channel, exc)
        raise
    await redis.publish(channel, encoded)
    logger.debug("realtime: sent event", extra={"channel": channel, "type": payload.get("type")})
