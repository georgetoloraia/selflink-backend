from __future__ import annotations

from django.core.cache import cache

from apps.social.models import Follow
from apps.users.models import User


def _cache_key(user_id: int) -> str:
    return f"soulmatch:pref:{user_id}"


def get_following_ids(user: User) -> set[int]:
    cache_key = _cache_key(user.id)
    cached = cache.get(cache_key)
    if isinstance(cached, set):
        return cached
    followee_ids = set(
        Follow.objects.filter(follower=user).values_list("followee_id", flat=True)
    )
    cache.set(cache_key, followee_ids, timeout=15 * 60)
    return followee_ids


def personalization_adjustment(user: User, candidate: User, following_ids: set[int]) -> int:
    """
    Lightweight personalization: small boost if user already follows candidate.
    """
    if candidate.id in following_ids:
        return 5
    return 0
