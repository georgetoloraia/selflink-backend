from __future__ import annotations

import logging
from textwrap import shorten

from django.core.cache import cache
from django.utils import timezone

from apps.mentor.models import MentorSession

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def _build_payload(title: str, subtitle: str, cta: str = "Open mentor") -> dict:
    return {"title": title, "subtitle": subtitle, "cta": cta}


def get_daily_feed_insight(user) -> dict:
    """
    Return a short per-user daily mentor insight for feed cards.
    - Uses today's daily mentor session if available (user-specific content).
    - Falls back to the most recent mentor session answer.
    - Returns a safe placeholder on errors or when nothing is available.
    The result is cached per-user-per-day to avoid repeated lookups/LLM calls.
    """
    today = timezone.localdate()
    cache_key = f"mentor:feed_insight:{user.id}:{today.isoformat()}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        # Prefer today's daily entry
        session = (
            MentorSession.objects.filter(user=user, mode=MentorSession.MODE_DAILY, date=today)
            .order_by("-created_at")
            .first()
        )
        # Fallback: latest mentor session with an answer
        if session is None:
            session = (
                MentorSession.objects.filter(user=user, answer__isnull=False)
                .order_by("-date", "-created_at")
                .first()
            )

        if session and session.answer:
            subtitle = shorten(session.answer.strip(), width=180, placeholder="…")
            payload = _build_payload("Today's insight", subtitle)
        else:
            payload = _placeholder_payload()

    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to build mentor feed insight for user %s: %s", user.id, exc, exc_info=True)
        payload = _placeholder_payload()

    cache.set(cache_key, payload, timeout=_CACHE_TTL_SECONDS)
    return payload


def _placeholder_payload() -> dict:
    return _build_payload(
        "Today's insight",
        "Daily mentor insight is not available right now. Tap to open Mentor.",
    )
