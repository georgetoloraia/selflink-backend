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
    - Uses stored matrix data or computes life path from birth date.
    - Falls back to a gentle prompt to add birth data when unavailable.
    The result is cached per-user-per-day for efficiency.
    """
    today = timezone.localdate()
    cache_key = f"matrix:feed_insight:{user.id}:{today.isoformat()}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        matrix, _ = MatrixData.objects.get_or_create(user=user)
        life_path = matrix.life_path
        traits = matrix.traits or {}

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
            payload = _build_payload("Today's matrix insight", subtitle)
        else:
            payload = _placeholder_payload()

    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to build matrix feed insight for user %s: %s", user.id, exc, exc_info=True)
        payload = _placeholder_payload()

    cache.set(cache_key, payload, timeout=_CACHE_TTL_SECONDS)
    return payload


def _placeholder_payload() -> dict:
    return _build_payload(
        "Today's matrix insight",
        "Add your birth data to unlock daily matrix insights tailored to you.",
    )
