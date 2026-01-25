from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from apps.realtime.publish import publish_realtime_event


def _payload() -> dict:
    return {"type": "gift.received", "id": 1}


@pytest.mark.django_db
def test_publish_http_success_skips_redis() -> None:
    with patch("apps.realtime.publish.requests.post") as mocked_post, patch(
        "apps.realtime.publish.publish_event"
    ) as mocked_redis:
        mocked_post.return_value = Mock(ok=True)
        publish_realtime_event("post:1", _payload(), context={"event_id": 1})
        assert mocked_post.called
        assert mocked_redis.called is False


@pytest.mark.django_db
def test_publish_http_failure_falls_back_to_redis() -> None:
    with patch("apps.realtime.publish.requests.post") as mocked_post, patch(
        "apps.realtime.publish.publish_event"
    ) as mocked_redis:
        mocked_post.return_value = Mock(ok=False, status_code=500)
        publish_realtime_event("post:1", _payload(), context={"event_id": 1})
        assert mocked_redis.called is True
