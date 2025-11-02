from __future__ import annotations

from statistics import mean
from typing import Dict

from django.db import transaction

from apps.matrix.models import AstroProfile, MatrixData
from apps.mentor.models import MentorMemory
from apps.reco.models import SoulMatchProfile
from apps.social.models import Follow
from apps.users.models import User

SENTIMENT_SCORES = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


def compute_sentiment_score(memory: MentorMemory | None) -> float:
    if not memory:
        return 0.0
    entries = memory.notes.get("entries", [])
    scores = [SENTIMENT_SCORES.get(entry.get("sentiment"), 0.0) for entry in entries]
    if not scores:
        return 0.0
    return mean(scores)


def compute_social_score(user: User) -> float:
    follow_count = Follow.objects.filter(follower=user).count()
    follower_count = Follow.objects.filter(followee=user).count()
    return follow_count * 0.6 + follower_count * 0.4


def build_traits(user: User, astro: AstroProfile | None, matrix: MatrixData | None, memory: MentorMemory | None) -> Dict[str, str]:
    traits: Dict[str, str] = {}
    if astro:
        traits["sun"] = astro.sun
        traits["moon"] = astro.moon
    if matrix:
        traits["life_path"] = matrix.life_path
        traits.update({f"matrix_{k}": v for k, v in (matrix.traits or {}).items()})
    if memory:
        traits["mentor_summary"] = memory.last_summary
    return traits


def refresh_soulmatch_profile(user: User) -> SoulMatchProfile:
    astro = getattr(user, "astro_profile", None)
    if astro is None:
        astro = AstroProfile.objects.filter(user=user).first()
    matrix = getattr(user, "matrix_data", None)
    if matrix is None:
        matrix = MatrixData.objects.filter(user=user).first()
    memory = getattr(user, "mentor_memory", None)
    if memory is None:
        memory = MentorMemory.objects.filter(user=user).first()

    sentiment = compute_sentiment_score(memory)
    social = compute_social_score(user)
    traits = build_traits(user, astro, matrix, memory)

    with transaction.atomic():
        profile, _ = SoulMatchProfile.objects.get_or_create(user=user)
        profile.sun = astro.sun if astro else ""
        profile.moon = astro.moon if astro else ""
        profile.life_path = matrix.life_path if matrix else ""
        profile.avg_sentiment = sentiment
        profile.social_score = social
        profile.traits = traits
        profile.save()
    return profile
