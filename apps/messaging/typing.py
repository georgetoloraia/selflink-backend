from __future__ import annotations

import time
from typing import List

from apps.core.pubsub import get_redis_client

TYPING_TTL_SECONDS = 7


def _key(thread_id: int) -> str:
    return f"typing:thread:{thread_id}"


def start_typing(user_id: int, thread_id: int) -> None:
    client = get_redis_client()
    client.hset(_key(thread_id), user_id, int(time.time()))
    client.expire(_key(thread_id), TYPING_TTL_SECONDS)


def stop_typing(user_id: int, thread_id: int) -> None:
    client = get_redis_client()
    client.hdel(_key(thread_id), user_id)


def get_typing_users(thread_id: int) -> List[int]:
    client = get_redis_client()
    entries = client.hgetall(_key(thread_id))
    now = time.time()
    active = []
    for raw_user_id, raw_ts in entries.items():
        if isinstance(raw_user_id, bytes):
            raw_user_id = raw_user_id.decode("utf-8", errors="ignore")
        if isinstance(raw_ts, bytes):
            raw_ts = raw_ts.decode("utf-8", errors="ignore")
        try:
            user_id = int(raw_user_id)
            ts = float(raw_ts)
        except (ValueError, TypeError):
            continue
        if now - ts <= TYPING_TTL_SECONDS:
            active.append(user_id)
    if not active:
        client.delete(_key(thread_id))
    return active
