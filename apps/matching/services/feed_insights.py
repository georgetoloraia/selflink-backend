from __future__ import annotations

import logging
from textwrap import shorten

from django.core.cache import cache
from django.utils import timezone

from apps.matching.services.soulmatch import calculate_soulmatch
from apps.users.models import User

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def _build_payload(title: str, subtitle: str, profiles: list[dict], cta: str = "View matches") -> dict:
    return {"title": title, "subtitle": subtitle, "profiles": profiles, "cta": cta}


def _placeholder_payload() -> dict:
    return _build_payload(
        "Unlock SoulMatch",
        "Add your birth data to see compatible connections tailored for you.",
        profiles=[],
        cta="Open SoulMatch",
    )


def get_daily_feed_recommendations(user: User, limit_profiles: int = 3) -> dict:
    """
    Return a small SoulMatch feed card payload for the given user.
    - First tries to read precomputed cache written by Celery.
    - Falls back to a lightweight placeholder to avoid heavy compute on request path.
    """
    today = timezone.localdate().isoformat()
    cache_keys = [
        f"soulmatch_insight:{user.id}:{today}",
        f"soulmatch:feed:{user.id}:{today}",  # legacy key
    ]
    for key in cache_keys:
        cached = cache.get(key)
        if cached:
            return cached

    # On cache miss, return a safe placeholder (heavy scoring handled by Celery)
    payload = _placeholder_payload()
    cache.set(cache_keys[0], payload, timeout=_CACHE_TTL_SECONDS)
    return payload


def compute_soulmatch_payload(user_id: int, limit_profiles: int = 3) -> dict:
    """
    Heavy-path computation used by Celery to precompute and store insights.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return _placeholder_payload()

    try:
        candidates = list(
            User.objects.exclude(id=user.id)
            .select_related("profile", "natal_chart", "birth_data", "astro_profile", "matrix_data")
            .only("id", "name", "photo", "handle", "birth_date")[:30]
        )

        recommendations: list[dict] = []
        for candidate in candidates:
            try:
                result = calculate_soulmatch(user, candidate)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(
                    "SoulMatch calculation failed for user %s -> %s: %s",
                    user.id,
                    candidate.id,
                    exc,
                    exc_info=True,
                )
                continue

            display_name = candidate.name or candidate.handle
            recommendations.append(
                {
                    "id": candidate.id,
                    "name": display_name,
                    "avatarUrl": candidate.photo,
                    "score": result.get("score"),
                }
            )

        if recommendations:
            recommendations.sort(key=lambda item: item.get("score") or 0, reverse=True)
            top_profiles = recommendations[:limit_profiles]
            names = [p["name"] for p in top_profiles if p.get("name")]
            if names:
                subtitle_raw = f"High compatibility with {', '.join(names)}."
            else:
                subtitle_raw = "You have high compatibility matches today."
            subtitle = shorten(subtitle_raw, width=180, placeholder="…")
            return _build_payload(
                "New SoulMatch connections",
                subtitle,
                profiles=top_profiles,
                cta="View matches",
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to compute soulmatch payload for user %s: %s", user_id, exc, exc_info=True)
    return _placeholder_payload()
