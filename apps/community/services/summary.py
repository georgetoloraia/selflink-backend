from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.community.models import (
    AgreementAcceptance,
    ArtifactComment,
    ProblemComment,
    ProblemWork,
    WorkArtifact,
)

User = get_user_model()


@dataclass(frozen=True)
class Money:
    amount: str
    currency: str


def _format_amount(value: Decimal | int | float) -> str:
    return f"{Decimal(value):.2f}"


def _distinct_user_ids() -> set[int]:
    ids: set[int] = set()
    id_sources: Iterable[Iterable[int]] = [
        AgreementAcceptance.objects.values_list("user_id", flat=True).distinct(),
        ProblemWork.objects.values_list("user_id", flat=True).distinct(),
        WorkArtifact.objects.values_list("user_id", flat=True).distinct(),
        ProblemComment.objects.values_list("user_id", flat=True).distinct(),
        ArtifactComment.objects.values_list("user_id", flat=True).distinct(),
    ]
    for source in id_sources:
        ids.update(source)
    return ids


def get_community_summary() -> dict:
    as_of = timezone.now()
    contributors_count = len(_distinct_user_ids())

    total_income = Money(amount=_format_amount(0), currency="USD")
    per_person = Decimal(total_income.amount) / contributors_count if contributors_count else Decimal(0)
    contributors_reward = Money(amount=_format_amount(per_person), currency="USD")

    return {
        "as_of": as_of,
        "total_income": {"amount": total_income.amount, "currency": total_income.currency},
        "contributors_reward": {
            "amount": contributors_reward.amount,
            "currency": contributors_reward.currency,
        },
        "contributors": {"count": contributors_count},
        "distribution_preview": [],
    }
