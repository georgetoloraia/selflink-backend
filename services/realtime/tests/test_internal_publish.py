from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.realtime.app import app
from services.realtime.config import settings


client = TestClient(app)


def _set_token(value: str) -> None:
    settings.realtime_publish_token = value


def test_internal_publish_requires_token() -> None:
    _set_token("secret")
    with patch("services.realtime.app.publish", new=AsyncMock()):
        response = client.post("/internal/publish", json={"channel": "post:1", "payload": {"type": "gift.received"}})
    assert response.status_code in {401, 403}


def test_internal_publish_rejects_invalid_token() -> None:
    _set_token("secret")
    with patch("services.realtime.app.publish", new=AsyncMock()):
        response = client.post(
            "/internal/publish",
            json={"channel": "post:1", "payload": {"type": "gift.received"}},
            headers={"Authorization": "Bearer wrong"},
        )
    assert response.status_code == 403


def test_internal_publish_rejects_invalid_channel() -> None:
    _set_token("secret")
    with patch("services.realtime.app.publish", new=AsyncMock()):
        response = client.post(
            "/internal/publish",
            json={"channel": "user:1", "payload": {"type": "gift.received"}},
            headers={"Authorization": "Bearer secret"},
        )
    assert response.status_code == 400


def test_internal_publish_rejects_invalid_event_type() -> None:
    _set_token("secret")
    with patch("services.realtime.app.publish", new=AsyncMock()):
        response = client.post(
            "/internal/publish",
            json={"channel": "post:1", "payload": {"type": "message:new"}},
            headers={"Authorization": "Bearer secret"},
        )
    assert response.status_code == 400
