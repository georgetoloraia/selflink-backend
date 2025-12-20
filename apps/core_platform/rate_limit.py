from __future__ import annotations

from django.conf import settings
from django.core.cache import cache


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    if not getattr(settings, "RATE_LIMITS_ENABLED", False):
        return False
    if limit <= 0 or window_seconds <= 0:
        return False

    cache_key = f"rl:{key}"
    try:
        if cache.add(cache_key, 1, timeout=window_seconds):
            return False
        current = cache.incr(cache_key)
    except Exception:
        return False

    return current > limit
