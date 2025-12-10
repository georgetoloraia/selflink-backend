from __future__ import annotations

from celery import shared_task

from apps.astro.models import BirthData
from apps.astro.services import chart_calculator


@shared_task
def compute_natal_chart_task(birth_data_id: int) -> int:
    birth_data = BirthData.objects.get(id=birth_data_id)
    chart = chart_calculator.calculate_natal_chart(birth_data)
    return chart.id
