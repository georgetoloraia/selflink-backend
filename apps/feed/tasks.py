from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from apps.matching.services.feed_insights import compute_soulmatch_payload
from apps.matrix.feed_insights import compute_matrix_payload
from apps.mentor.services.feed_insights import compute_mentor_payload
from apps.social.models import Timeline
from services.reco.jobs import rebuild_user_timeline

logger = logging.getLogger(__name__)


@shared_task
def prune_old_timeline_entries(days: int = 30) -> int:
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = Timeline.objects.filter(created_at__lt=cutoff).delete()
    return deleted


@shared_task
def rebuild_user_timeline_task(user_id: int) -> dict:
    considered, written = rebuild_user_timeline(user_id)
    return {"considered": considered, "written": written}


@shared_task
def compute_daily_mentor_insight(user_id: int) -> dict:
    today = timezone.localdate().isoformat()
    cache_key = f"mentor_insight:{user_id}:{today}"
    try:
        payload = compute_mentor_payload(user_id)
        cache.set(cache_key, payload, 24 * 60 * 60)
        return payload
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Mentor insight task failed for user %s: %s", user_id, exc, exc_info=True)
        return {}


@shared_task
def compute_daily_matrix_insight(user_id: int) -> dict:
    today = timezone.localdate().isoformat()
    cache_key = f"matrix_insight:{user_id}:{today}"
    try:
        payload = compute_matrix_payload(user_id)
        cache.set(cache_key, payload, 24 * 60 * 60)
        return payload
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Matrix insight task failed for user %s: %s", user_id, exc, exc_info=True)
        return {}


@shared_task
def compute_daily_soulmatch_insight(user_id: int) -> dict:
    today = timezone.localdate().isoformat()
    cache_key = f"soulmatch_insight:{user_id}:{today}"
    try:
        payload = compute_soulmatch_payload(user_id)
        cache.set(cache_key, payload, 24 * 60 * 60)
        return payload
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("SoulMatch insight task failed for user %s: %s", user_id, exc, exc_info=True)
        return {}
