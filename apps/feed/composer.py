from __future__ import annotations

import logging
from typing import Iterable, List, Sequence
from urllib.parse import parse_qs, urlparse

from django.core.cache import cache
from django.utils import timezone

from django.db.models import Q

from apps.matching.services.feed_insights import get_daily_feed_recommendations
from apps.matrix.feed_insights import get_daily_feed_insight as get_matrix_feed_insight
from apps.mentor.services.feed_insights import get_daily_feed_insight as get_mentor_feed_insight
from apps.social.models import Follow, Post, Timeline
from apps.social.serializers import PostSerializer
from apps.feed.rank import (
    FEED_RANKING_CONFIG_FOR_YOU,
    FEED_RANKING_CONFIG_FOR_YOU_VIDEOS,
    score_post_for_user,
)

logger = logging.getLogger(__name__)


def compose_home_feed_items(
    timeline_entries: Iterable[Timeline],
    serializer_context: dict | None = None,
    user=None,
) -> list[dict]:
    """
    Build the typed feed item list from timeline entries or post iterables, wrapping posts and
    inserting mentor/matrix/soulmatch insight cards derived from real services.
    """
    entries: List = list(timeline_entries)

    posts = [
        getattr(entry, "post", entry)
        for entry in entries
        if getattr(entry, "post", entry) is not None
    ] if entries else []

    post_data = (
        PostSerializer(
            posts,
            many=True,
            context=serializer_context or {},
        ).data
        if posts
        else []
    )

    post_items = [
        {"type": "post", "id": post["id"], "post": post}
        for post in post_data
    ]
    return _insert_insights(post_items, user=user)


def extract_cursor_from_url(url: str | None, cursor_param: str = "cursor") -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    values = params.get(cursor_param)
    return values[0] if values else None


def _insert_insights(post_items: Sequence[dict], user=None) -> list[dict]:
    base_items = list(post_items)

    today_iso = timezone.localdate().isoformat()
    mentor_payload = None
    matrix_payload = None
    soulmatch_payload = None

    if user:
        if not base_items:
            mentor_payload = cache.get(f"mentor_insight:{user.id}:{today_iso}") or cache.get(
                f"mentor:feed_insight:{user.id}:{today_iso}"
            )
            matrix_payload = cache.get(f"matrix_insight:{user.id}:{today_iso}") or cache.get(
                f"matrix:feed_insight:{user.id}:{today_iso}"
            )
            soulmatch_payload = cache.get(f"soulmatch_insight:{user.id}:{today_iso}") or cache.get(
                f"soulmatch:feed:{user.id}:{today_iso}"
            )
            if not any([mentor_payload, matrix_payload, soulmatch_payload]):
                return base_items
        else:
            try:
                mentor_payload = get_mentor_feed_insight(user)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Mentor insight unavailable for user %s: %s",
                    getattr(user, "id", None),
                    exc,
                    exc_info=True,
                )
            try:
                matrix_payload = get_matrix_feed_insight(user)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Matrix insight unavailable for user %s: %s",
                    getattr(user, "id", None),
                    exc,
                    exc_info=True,
                )
            try:
                soulmatch_payload = get_daily_feed_recommendations(user)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "SoulMatch insight unavailable for user %s: %s",
                    getattr(user, "id", None),
                    exc,
                    exc_info=True,
                )

    mentor_item = (
        {
            "type": "mentor_insight",
            "id": f"mentor_{today_iso}",
            "mentor": mentor_payload,
        }
        if mentor_payload
        else None
    )
    matrix_item = (
        {
            "type": "matrix_insight",
            "id": f"matrix_{today_iso}",
            "matrix": matrix_payload,
        }
        if matrix_payload
        else None
    )
    soulmatch_item = (
        {
            "type": "soulmatch_reco",
            "id": f"soulmatch_{today_iso}",
            "soulmatch": soulmatch_payload,
        }
        if soulmatch_payload
        else None
    )

    composed = list(base_items)
    mentor_index = None
    matrix_index = None
    if mentor_item:
        mentor_index = min(2, len(composed))
        composed.insert(mentor_index, mentor_item)

    base_count = len(base_items)
    if base_count >= 6 and matrix_item:
        matrix_index = min(6, base_count)
        if mentor_item and mentor_index is not None and mentor_index <= matrix_index:
            matrix_index += 1
        matrix_index = min(matrix_index, len(composed))
        composed.insert(matrix_index, matrix_item)

    if soulmatch_item:
        target_index = min(4, len(composed))
        if mentor_index is not None and mentor_index <= target_index:
            target_index += 1
        if matrix_index is not None and matrix_index <= target_index:
            target_index += 1
        target_index = min(target_index, len(composed))
        composed.insert(target_index, soulmatch_item)

    return composed


def compose_following_feed(user, cursor: str | None = None, limit: int = 20, serializer_context: dict | None = None):
    """
    Chronological feed for followed users (and user's own posts) using timeline entries.
    """
    queryset = (
        Timeline.objects.filter(user=user)
        .select_related("post", "post__author", "post__author__settings")
        .select_related("post__video")
        .prefetch_related("post__media", "post__images")
        .order_by("-created_at")
    )
    entries, next_cursor = _slice_with_cursor(queryset, cursor=cursor, limit=limit)
    items = compose_home_feed_items(entries, serializer_context=serializer_context, user=user)
    return items, next_cursor


def compose_for_you_feed(user, cursor: str | None = None, limit: int = 20, serializer_context: dict | None = None):
    """
    Ranked feed using simple scoring over recent posts.
    """
    # candidate pool: recent posts visible to the user
    followee_ids = set(
        Follow.objects.filter(follower=user).values_list("followee_id", flat=True)
    )
    visibility_filter = (
        Q(visibility=Post.Visibility.PUBLIC)
        | Q(author=user)
        | (Q(visibility=Post.Visibility.FOLLOWERS) & Q(author_id__in=followee_ids))
    )
    candidate_limit = max(limit * 3, limit + 10)
    candidates = list(
        Post.objects.filter(visibility_filter)
        .select_related("author", "author__settings", "video")
        .prefetch_related("media", "images")
        .order_by("-created_at")[:candidate_limit]
    )

    scored = [
        (post, score_post_for_user(user, post, FEED_RANKING_CONFIG_FOR_YOU, followee_ids=followee_ids))
        for post in candidates
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    offset = _parse_cursor(cursor)
    page_slice = scored[offset : offset + limit + 1]
    has_next = len(page_slice) > limit
    if has_next:
        page_slice = page_slice[:limit]
    posts_page = [pair[0] for pair in page_slice]
    items = compose_home_feed_items(posts_page, serializer_context=serializer_context, user=user)
    next_cursor = str(offset + limit) if has_next else None
    return items, next_cursor


def compose_for_you_videos_feed(
    user,
    cursor: str | None = None,
    limit: int = 20,
    serializer_context: dict | None = None,
):
    """
    Compose a video-only "For You" feed.
    - Filters posts to those that have an attached PostVideo.
    - Applies existing ranking but excludes insight insertions.
    - Returns typed items with type="post" only.
    """
    followee_ids = set(
        Follow.objects.filter(follower=user).values_list("followee_id", flat=True)
    )
    visibility_filter = (
        Q(video__isnull=False)
        & (
            Q(visibility=Post.Visibility.PUBLIC)
            | Q(author=user)
            | (Q(visibility=Post.Visibility.FOLLOWERS) & Q(author_id__in=followee_ids))
        )
    )
    candidate_limit = max(limit * 3, limit + 10)
    candidates = list(
        Post.objects.filter(visibility_filter)
        .select_related("author", "author__settings", "video")
        .prefetch_related("media", "images")
        .order_by("-created_at")[:candidate_limit]
    )

    scored = [
        (post, score_post_for_user(user, post, FEED_RANKING_CONFIG_FOR_YOU_VIDEOS, followee_ids=followee_ids))
        for post in candidates
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    offset = _parse_cursor(cursor)
    page_slice = scored[offset : offset + limit + 1]
    has_next = len(page_slice) > limit
    if has_next:
        page_slice = page_slice[:limit]
    posts_page = [pair[0] for pair in page_slice]
    post_data = PostSerializer(
        posts_page,
        many=True,
        context=serializer_context or {},
    ).data
    items = [
        {"type": "post", "id": post["id"], "post": post}
        for post in post_data
    ]
    next_cursor = str(offset + limit) if has_next else None
    return items, next_cursor


def _parse_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(cursor))
    except ValueError:
        return 0


def _slice_with_cursor(queryset, cursor: str | None, limit: int):
    offset = _parse_cursor(cursor)
    slice_qs = list(queryset[offset : offset + limit + 1])
    has_next = len(slice_qs) > limit
    entries = slice_qs[:limit]
    next_cursor = str(offset + limit) if has_next else None
    return entries, next_cursor
