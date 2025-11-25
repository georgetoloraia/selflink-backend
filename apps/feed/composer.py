from __future__ import annotations

import logging
from typing import Iterable, List, Sequence
from urllib.parse import parse_qs, urlparse

from django.utils import timezone

from apps.matrix.services.feed_insights import get_daily_feed_insight as get_matrix_feed_insight
from apps.mentor.services.feed_insights import get_daily_feed_insight as get_mentor_feed_insight
from apps.social.models import Timeline
from apps.social.serializers import PostSerializer

logger = logging.getLogger(__name__)


def compose_home_feed_items(
    timeline_entries: Iterable[Timeline],
    serializer_context: dict | None = None,
    user=None,
) -> list[dict]:
    """
    Build the typed feed item list from timeline entries, wrapping posts and
    inserting mentor/matrix insight cards derived from real services.
    """
    entries: List[Timeline] = list(timeline_entries)
    if not entries:
        return []

    post_data = PostSerializer(
        [entry.post for entry in entries],
        many=True,
        context=serializer_context or {},
    ).data

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
    if not base_items:
        return base_items

    today_iso = timezone.localdate().isoformat()
    mentor_payload = None
    matrix_payload = None

    if user:
        try:
            mentor_payload = get_mentor_feed_insight(user)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Mentor insight unavailable for user %s: %s", getattr(user, "id", None), exc, exc_info=True)
        try:
            matrix_payload = get_matrix_feed_insight(user)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Matrix insight unavailable for user %s: %s", getattr(user, "id", None), exc, exc_info=True)

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

    composed = list(base_items)
    mentor_index = min(2, len(composed))
    if mentor_item:
        composed.insert(mentor_index, mentor_item)

    base_count = len(base_items)
    if base_count >= 6 and matrix_item:
        matrix_index = min(6, base_count)
        if mentor_item and mentor_index <= matrix_index:
            matrix_index += 1
        matrix_index = min(matrix_index, len(composed))
        composed.insert(matrix_index, matrix_item)

    return composed
