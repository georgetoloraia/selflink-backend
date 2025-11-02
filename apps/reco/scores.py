from __future__ import annotations

from math import exp
from typing import Dict, Iterable

from django.db import transaction

from apps.matrix.models import AstroProfile, MatrixData
from apps.reco.models import SoulMatchProfile, SoulMatchScore
from apps.reco.services import refresh_soulmatch_profile
from apps.users.models import User


def _compatibility(a: SoulMatchProfile, b: SoulMatchProfile) -> Dict[str, float]:
    astro_score = 0.0
    if a.sun and b.sun and a.sun == b.sun:
        astro_score += 20
    if a.moon and b.moon and a.moon == b.moon:
        astro_score += 20
    if a.life_path and b.life_path and a.life_path == b.life_path:
        astro_score += 30

    sentiment_score = 10 - abs(a.avg_sentiment - b.avg_sentiment) * 5
    social_score = min(a.social_score, b.social_score) * 0.1

    total = astro_score + sentiment_score + social_score
    return {
        "total": total,
        "astro": astro_score,
        "sentiment": sentiment_score,
        "social": social_score,
    }


def compute_soulmatch_scores(user: User, candidates: Iterable[User]) -> None:
    user_profile = refresh_soulmatch_profile(user)
    candidate_profiles = {candidate.id: refresh_soulmatch_profile(candidate) for candidate in candidates}

    with transaction.atomic():
        for candidate_id, profile in candidate_profiles.items():
            if candidate_id == user.id:
                continue
            breakdown = _compatibility(user_profile, profile)
            normalized = 1 / (1 + exp(-breakdown["total"] / 50))
            SoulMatchScore.objects.update_or_create(
                user=user,
                target_id=candidate_id,
                defaults={
                    "score": round(normalized, 4),
                    "breakdown": breakdown,
                },
            )
