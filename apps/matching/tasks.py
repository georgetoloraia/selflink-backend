from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model

from apps.matching.models import SoulMatchResult
from apps.matching.services.soulmatch import calculate_soulmatch

User = get_user_model()


def _pair_key(user_a_id: int, user_b_id: int) -> str:
    return f"{min(user_a_id, user_b_id)}:{max(user_a_id, user_b_id)}"


def _result_from_payload(payload: dict[str, object]) -> dict[str, object]:
    result = dict(payload)
    for key in ("pair_key", "rules_version", "user_a_id", "user_b_id"):
        result.pop(key, None)
    return result


def _compute_and_store(user_a_id: int, user_b_id: int, rules_version: str) -> dict[str, object]:
    pair_key = _pair_key(user_a_id, user_b_id)
    existing = SoulMatchResult.objects.filter(pair_key=pair_key, rules_version=rules_version).first()
    if existing:
        return _result_from_payload(existing.payload_json)

    user_a = User.objects.get(id=user_a_id)
    user_b = User.objects.get(id=user_b_id)
    result = calculate_soulmatch(user_a, user_b)
    payload = {
        "pair_key": pair_key,
        "rules_version": rules_version,
        "user_a_id": user_a_id,
        "user_b_id": user_b_id,
        **result,
    }

    try:
        with transaction.atomic():
            SoulMatchResult.objects.create(
                pair_key=pair_key,
                rules_version=rules_version,
                score=float(result.get("score", 0)),
                payload_json=payload,
            )
    except IntegrityError:
        existing = SoulMatchResult.objects.get(pair_key=pair_key, rules_version=rules_version)
        return existing.payload_json

    return result


@shared_task
def calculate_soulmatch_task(user_a_id: int, user_b_id: int) -> dict[str, object]:
    rules_version = getattr(settings, "MATCH_RULES_VERSION", "v1")
    return _compute_and_store(user_a_id, user_b_id, rules_version)


@shared_task
def soulmatch_compute_score_task(user_a_id: int, user_b_id: int, rules_version: str | None = None) -> dict[str, object]:
    rules_version = rules_version or getattr(settings, "MATCH_RULES_VERSION", "v1")
    return _compute_and_store(user_a_id, user_b_id, rules_version)
