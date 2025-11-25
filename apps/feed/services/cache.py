from __future__ import annotations

from typing import Any

from django.core.cache import cache


class FeedCache:
    """
    Manages per-user feed caching for:
      - for_you
      - following
    Caches page results including typed items + next cursor.
    """

    @staticmethod
    def make_key(user_id: int, mode: str, cursor: str | None) -> str:
        cursor_part = cursor if cursor not in (None, "") else "none"
        return f"feed:{mode}:{user_id}:cursor_{cursor_part}"

    @staticmethod
    def get(user_id: int, mode: str, cursor: str | None) -> dict | None:
        key = FeedCache.make_key(user_id, mode, cursor)
        data: Any = cache.get(key)
        if isinstance(data, dict) and "items" in data and "next" in data:
            return data
        return None

    @staticmethod
    def set(user_id: int, mode: str, cursor: str | None, payload: dict, ttl_seconds: int = 60) -> None:
        key = FeedCache.make_key(user_id, mode, cursor)
        cache.set(key, payload, ttl_seconds)

    @staticmethod
    def invalidate_first_page(user_id: int) -> None:
        """
        Remove cache keys where cursor=None for both 'for_you' and 'following'.
        Only page 1 should be invalidated for performance.
        """
        for mode in ("for_you", "following"):
            key = FeedCache.make_key(user_id, mode, None)
            cache.delete(key)
