from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model

from apps.matching.services.soulmatch import calculate_soulmatch

User = get_user_model()


@shared_task
def calculate_soulmatch_task(user_a_id: int, user_b_id: int) -> dict[str, object]:
    user_a = User.objects.get(id=user_a_id)
    user_b = User.objects.get(id=user_b_id)
    return calculate_soulmatch(user_a, user_b)
