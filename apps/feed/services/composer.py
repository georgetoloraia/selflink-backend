from __future__ import annotations

from typing import Iterable, List, Sequence
from urllib.parse import parse_qs, urlparse

from django.utils import timezone

from apps.social.models import Timeline
from apps.social.serializers import PostSerializer


def compose_home_feed_items(
    timeline_entries: Iterable[Timeline],
    serializer_context: dict | None = None,
) -> list[dict]:
    """
    Build the typed feed item list from timeline entries, wrapping posts and
    inserting simple mentor/matrix insight placeholders.
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
    return _insert_insights(post_items)


def extract_cursor_from_url(url: str | None, cursor_param: str = "cursor") -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    values = params.get(cursor_param)
    return values[0] if values else None


def _insert_insights(post_items: Sequence[dict]) -> list[dict]:
    base_items = list(post_items)
    if not base_items:
        return base_items

    today_iso = timezone.localdate().isoformat()
    mentor_item = {
        "type": "mentor_insight",
        "id": f"mentor_{today_iso}",
        "mentor": {
            "title": "Today's insight",
            "subtitle": "Short daily guidance. (Placeholder from backend)",
            "cta": "Open mentor",
        },
    }
    matrix_item = {
        "type": "matrix_insight",
        "id": f"matrix_{today_iso}",
        "matrix": {
            "title": "Today's matrix line",
            "subtitle": "Short matrix/astro hint. (Placeholder from backend)",
            "cta": "View matrix",
        },
    }

    composed = list(base_items)
    mentor_index = min(2, len(composed))
    composed.insert(mentor_index, mentor_item)

    base_count = len(base_items)
    if base_count >= 6:
        matrix_index = min(6, base_count)
        if mentor_index <= matrix_index:
            matrix_index += 1
        matrix_index = min(matrix_index, len(composed))
        composed.insert(matrix_index, matrix_item)

    return composed
