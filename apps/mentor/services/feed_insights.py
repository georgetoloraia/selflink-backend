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
    - First tries to read precomputed cache written by Celery.
    - Falls back to a lightweight DB read of latest mentor session answer.
    - Returns a safe placeholder on errors or when nothing is available.
    """
    today = timezone.localdate().isoformat()
    cache_keys = [
        f"mentor_insight:{user.id}:{today}",
        f"mentor:feed_insight:{user.id}:{today}",  # legacy key
    ]
    for key in cache_keys:
        cached = cache.get(key)
        if cached:
            return cached

    try:
        session = (
            MentorSession.objects.filter(user=user, mode=MentorSession.MODE_DAILY, date=today)
            .order_by("-created_at")
            .first()
        )
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

    cache.set(cache_keys[0], payload, timeout=_CACHE_TTL_SECONDS)
    return payload


def compute_mentor_payload(user_id: int) -> dict:
    """
    Heavy-path computation used by Celery to precompute and store insights.
    """
    try:
        session = (
            MentorSession.objects.filter(user_id=user_id, mode=MentorSession.MODE_DAILY, date=timezone.localdate())
            .order_by("-created_at")
            .first()
        )
        if session is None:
            session = (
                MentorSession.objects.filter(user_id=user_id, answer__isnull=False)
                .order_by("-date", "-created_at")
                .first()
            )
        if session and session.answer:
            subtitle = shorten(session.answer.strip(), width=180, placeholder="…")
            return _build_payload("Today's insight", subtitle)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to compute mentor payload for user %s: %s", user_id, exc, exc_info=True)
    return _placeholder_payload()


def _placeholder_payload() -> dict:
    return _build_payload(
        "Today's insight",
        "Daily mentor insight is not available right now. Tap to open Mentor.",
    )
