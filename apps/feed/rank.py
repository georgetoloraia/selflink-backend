from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from apps.social.models import Follow

# Tunable weights for simple ranking model
W_RECENCY = 60.0
W_ENGAGEMENT = 25.0
W_RELATIONSHIP = 20.0

# How many hours until recency fully decays
RECENCY_DECAY_HOURS = 24 * 7  # 7 days


def _recency_factor(created_at: datetime) -> float:
    now = datetime.now(dt_timezone.utc)
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    decay = max(0.0, 1.0 - age_hours / RECENCY_DECAY_HOURS)
    return decay


def _engagement_factor(like_count: int, comment_count: int) -> float:
    return like_count * 0.5 + comment_count * 1.0


def _relationship_factor(author_id: int, follower_id: int, followee_ids: set[int] | None = None) -> float:
    if followee_ids is None:
        followee_ids = set(
            Follow.objects.filter(follower_id=follower_id).values_list("followee_id", flat=True)
        )
    return 1.0 if author_id in followee_ids else 0.0


def score_post_for_user(user, post, followee_ids: set[int] | None = None) -> float:
    """
    Compute a simple ranking score combining recency, engagement, and relationship.
    """
    recency = _recency_factor(post.created_at)
    engagement = _engagement_factor(getattr(post, "like_count", 0) or 0, getattr(post, "comment_count", 0) or 0)
    relationship = _relationship_factor(post.author_id, user.id, followee_ids=followee_ids)

    score = (
        W_RECENCY * recency
        + W_ENGAGEMENT * engagement
        + W_RELATIONSHIP * relationship
    )
    # small bonus to break ties by newer posts
    score += recency * 5.0
    return float(score)
