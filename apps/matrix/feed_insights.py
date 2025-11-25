from __future__ import annotations

import logging
from textwrap import shorten

from django.core.cache import cache
from django.utils import timezone

from apps.matrix.models import MatrixData
from apps.matrix.services import compute_life_path

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def _build_payload(title: str, subtitle: str, cta: str = "View matrix") -> dict:
    return {"title": title, "subtitle": subtitle, "cta": cta}


def get_daily_feed_insight(user) -> dict:
    """
    Return a short per-user matrix insight for the feed.
    - First tries to read precomputed cache written by Celery.
    - Falls back to a lightweight compute from stored birth/matrix data.
    """
    today = timezone.localdate().isoformat()
    cache_keys = [
        f"matrix_insight:{user.id}:{today}",
        f"matrix:feed_insight:{user.id}:{today}",  # legacy key
    ]
    for key in cache_keys:
        cached = cache.get(key)
        if cached:
            return cached

    payload = compute_matrix_payload(user.id)
    cache.set(cache_keys[0], payload, timeout=_CACHE_TTL_SECONDS)
    return payload


def compute_matrix_payload(user_id: int) -> dict:
    try:
        matrix, _ = MatrixData.objects.get_or_create(user_id=user_id)
        life_path = matrix.life_path
        traits = matrix.traits or {}

        from apps.users.models import User  # local import to avoid cycles

        user = User.objects.get(id=user_id)

        if not life_path and user.birth_date:
            life_path, traits = compute_life_path(user.birth_date)
            matrix.life_path = life_path
            matrix.traits = traits
            matrix.save(update_fields=["life_path", "traits", "updated_at"])

        if life_path:
            primary_trait = (traits.get("primary_trait") or traits.get("trait") or "").strip()
            trait_text = f" - {primary_trait}" if primary_trait else ""
            subtitle_raw = f"Your life path {life_path}{trait_text}. Lean into this energy today."
            subtitle = shorten(subtitle_raw, width=180, placeholder="…")
            return _build_payload("Today's matrix insight", subtitle)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to compute matrix payload for user %s: %s", user_id, exc, exc_info=True)
    return _placeholder_payload()


def _placeholder_payload() -> dict:
    return _build_payload(
        "Today's matrix insight",
        "Add your birth data to unlock daily matrix insights tailored to you.",
    )
