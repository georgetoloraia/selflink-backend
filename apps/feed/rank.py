from __future__ import annotations

import math
from dataclasses import dataclass

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from apps.social.models import Follow

# How quickly recency decays; higher values keep older posts competitive longer.
RECENCY_HALF_LIFE_HOURS = 24.0
# Normalizer to keep engagement signals bounded between 0 and 1.
ENGAGEMENT_NORMALIZER = 50.0
# Comments are generally stronger intent than likes; this keeps the signal monotonic while rewarding comments.
COMMENT_ENGAGEMENT_MULTIPLIER = 2.0


@dataclass(frozen=True)
class FeedRankingConfig:
    recency_weight: float
    like_weight: float
    comment_weight: float
    follow_author_weight: float
    base_engagement_bias: float
    video_bonus_weight: float
    matrix_alignment_weight: float = 0.0
    daily_energy_alignment_weight: float = 0.0


FEED_RANKING_CONFIG_FOR_YOU = FeedRankingConfig(
    recency_weight=0.55,
    like_weight=0.25,
    comment_weight=0.35,
    follow_author_weight=0.45,
    base_engagement_bias=0.05,
    video_bonus_weight=0.05,
)

FEED_RANKING_CONFIG_FOR_YOU_VIDEOS = FeedRankingConfig(
    recency_weight=0.45,
    like_weight=0.4,
    comment_weight=0.45,
    follow_author_weight=0.3,
    base_engagement_bias=0.05,
    video_bonus_weight=0.15,
)


def compute_recency_score(post) -> float:
    """
    Exponential decay over time so fresh posts dominate while older high-signal posts can still surface.
    """
    created_at = getattr(post, "created_at", None)
    if not created_at:
        return 0.0

    now = timezone.now()
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    # exp(-ln(2) * t / half_life) halves the score every RECENCY_HALF_LIFE_HOURS.
    decay = math.exp(-math.log(2) * age_hours / RECENCY_HALF_LIFE_HOURS)
    return float(decay)


def compute_engagement_score(post) -> tuple[float, float]:
    """
    Log-scaled engagement for likes and comments to avoid runaway scores from viral but stale posts.
    Returns (like_score, comment_score), each bounded between 0 and 1.
    """
    raw_likes = max(0, getattr(post, "like_count", 0) or 0)
    raw_comments = max(0, getattr(post, "comment_count", 0) or 0)

    like_score = math.log1p(raw_likes) / math.log1p(ENGAGEMENT_NORMALIZER)
    comment_score = math.log1p(raw_comments * COMMENT_ENGAGEMENT_MULTIPLIER) / math.log1p(ENGAGEMENT_NORMALIZER)

    return float(min(like_score, 1.0)), float(min(comment_score, 1.0))


def compute_follow_relationship_score(user, post, followee_ids: set[int] | None = None) -> float:
    """
    Boolean follow relationship for now; callers can provide a precomputed followee_id set to avoid extra queries.
    """
    if followee_ids is None:
        followee_ids = set(
            Follow.objects.filter(follower_id=getattr(user, "id", None)).values_list("followee_id", flat=True)
        )
    author_id = getattr(post, "author_id", None)
    return 1.0 if author_id in followee_ids else 0.0


def compute_video_flag(post) -> float:
    """
    Returns 1.0 when the post has an attached video, 0.0 otherwise.
    """
    if getattr(post, "_video_stub", None) is not None:
        return 1.0
    try:
        return 1.0 if getattr(post, "video", None) is not None else 0.0
    except ObjectDoesNotExist:
        return 0.0


def compute_matrix_alignment(user, post) -> float:
    """
    Placeholder hook for future matrix alignment scoring.
    """
    return 0.0


def compute_daily_energy_alignment(user, post) -> float:
    """
    Placeholder hook for future astro/daily energy scoring.
    """
    return 0.0


def score_post_for_user(user, post, config: FeedRankingConfig, followee_ids: set[int] | None = None) -> float:
    """
    Configurable ranking score combining recency, engagement, relationship, and future hooks.
    """
    recency = compute_recency_score(post)
    like_score, comment_score = compute_engagement_score(post)
    relationship = compute_follow_relationship_score(user, post, followee_ids=followee_ids or set())
    video_flag = compute_video_flag(post)

    score = (
        config.recency_weight * recency
        + config.like_weight * like_score
        + config.comment_weight * comment_score
        + config.follow_author_weight * relationship
        + config.video_bonus_weight * video_flag
        + config.matrix_alignment_weight * compute_matrix_alignment(user, post)
        + config.daily_energy_alignment_weight * compute_daily_energy_alignment(user, post)
        + config.base_engagement_bias
    )
    return float(score)
