from __future__ import annotations

from functools import lru_cache
from typing import Optional

from django.core.cache import cache

from .models import FeatureFlag

CACHE_KEY_PREFIX = "feature_flag:"
CACHE_TIMEOUT = 60  # seconds


def get_flag(key: str) -> Optional[FeatureFlag]:
    cache_key = f"{CACHE_KEY_PREFIX}{key}"
    flag = cache.get(cache_key)
    if flag is None:
        flag = FeatureFlag.objects.filter(key=key).first()
        cache.set(cache_key, flag, CACHE_TIMEOUT)
    return flag


def is_enabled(key: str, user_id: int | None = None, default: bool = False) -> bool:
    flag = get_flag(key)
    if not flag:
        return default
    if not flag.enabled:
        return False
    if flag.rollout <= 0:
        return True
    if flag.rollout >= 100:
        return True
    if user_id is None:
        return flag.rollout >= 100
    # deterministic bucketing based on user_id
    bucket = user_id % 100
    return bucket < int(flag.rollout)


def invalidate_cache(key: str) -> None:
    cache.delete(f"{CACHE_KEY_PREFIX}{key}")
    list_flags.cache_clear()


@lru_cache(maxsize=32)
def list_flags() -> list[str]:
    return list(FeatureFlag.objects.values_list("key", flat=True))
