from __future__ import annotations

import json
from functools import lru_cache

from redis.asyncio import Redis

from .config import settings


@lru_cache(maxsize=1)
def get_async_redis() -> Redis:
    return Redis.from_url(settings.redis_url)


async def publish(channel: str, payload: dict) -> None:
    redis = get_async_redis()
    await redis.publish(channel, json.dumps(payload))
