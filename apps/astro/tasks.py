from __future__ import annotations

from celery import shared_task

from apps.astro.models import BirthData
from apps.astro.cache import get_cached_or_compute


@shared_task
def compute_natal_chart_task(birth_data_id: int) -> int:
    birth_data = BirthData.objects.get(id=birth_data_id)
    _, chart = get_cached_or_compute(birth_data)
    return chart.id


@shared_task
def astrology_compute_birth_chart_task(birth_data_id: int, rules_version: str | None = None) -> int:
    """
    Background computation for deterministic astrology outputs.
    """
    birth_data = BirthData.objects.get(id=birth_data_id)
    _, chart = get_cached_or_compute(birth_data, rules_version=rules_version)
    return chart.id
