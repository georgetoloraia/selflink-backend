from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.social.models import Timeline
from services.reco.jobs import rebuild_user_timeline


@shared_task
def prune_old_timeline_entries(days: int = 30) -> int:
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = Timeline.objects.filter(created_at__lt=cutoff).delete()
    return deleted


@shared_task
def rebuild_user_timeline_task(user_id: int) -> dict:
    considered, written = rebuild_user_timeline(user_id)
    return {"considered": considered, "written": written}
