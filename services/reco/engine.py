from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Tuple

from apps.social.models import Follow, Post, Timeline, PostVisibility
from apps.users.models import User


def score_post(post: Post, relationship_weight: float = 1.0) -> float:
    now = datetime.now(timezone.utc)
    created = post.created_at or now
    age_hours = max((now - created).total_seconds() / 3600, 0.001)
    engagement = 1 + (post.like_count * 0.5) + (post.comment_count * 0.75)
    return (relationship_weight * engagement) / age_hours


def follow_relationship_weight(follow: Follow) -> float:
    # Simple heuristic: more recent follows = stronger weight
    now = datetime.now(timezone.utc)
    delta_hours = max((now - follow.created_at).total_seconds() / 3600, 1)
    return max(0.5, min(2.5, 3.0 / delta_hours))


def select_candidate_posts(user: User, follow_ids: Iterable[int], limit: int = 200) -> List[Post]:
    return list(
        Post.objects.filter(author_id__in=follow_ids, visibility__in=[PostVisibility.PUBLIC, PostVisibility.FOLLOWERS])
        .select_related("author", "author__settings")
        .prefetch_related("media")
        .order_by("-created_at")[:limit]
    )


def rebuild_timeline(user: User, follows: Iterable[Follow], limit: int = 200) -> Tuple[int, int]:
    follow_list = list(follows)
    follow_ids = [follow.followee_id for follow in follow_list]
    posts = select_candidate_posts(user, follow_ids, limit=limit)

    scored_entries = []
    follow_weights = {follow.followee_id: follow_relationship_weight(follow) for follow in follow_list}
    for post in posts:
        weight = follow_weights.get(post.author_id, 1.0)
        scored_entries.append((post, score_post(post, relationship_weight=weight)))

    timeline_objs = [
        Timeline(user=user, post=post, score=score)
        for post, score in scored_entries
    ]
    Timeline.objects.filter(user=user).delete()
    Timeline.objects.bulk_create(timeline_objs)
    return len(posts), len(timeline_objs)
