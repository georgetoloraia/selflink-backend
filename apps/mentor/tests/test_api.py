import json
from typing import Iterable

import pytest
from unittest import mock
from rest_framework.test import APIClient

from apps.mentor.models import MentorMessage, MentorSession
from apps.users.models import User


class _DummyResponse:
    status_code = 200

    def __init__(self, lines: Iterable[str]):
        self._lines = list(lines)

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = True):
        for line in self._lines:
            yield line


def _mock_streaming_post(*args, **kwargs):
    stream = kwargs.get("stream", False)
    if not stream:
        return _DummyResponse([json.dumps({"response": "Hello", "done": True})])
    lines = [
        json.dumps({"response": "Hello", "done": False}),
        json.dumps({"response": " world", "done": False}),
        json.dumps({"response": "", "done": True}),
    ]
    return _DummyResponse(lines)


@pytest.mark.django_db
def test_chat_requires_auth():
    client = APIClient()
    resp = client.post("/api/v1/mentor/chat/", {"message": "hi"}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_chat_returns_reply_and_saves_messages(monkeypatch):
    monkeypatch.setattr("apps.mentor.services.llm_client.requests.post", _mock_streaming_post)
    user = User.objects.create_user(email="test@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/v1/mentor/chat/",
        {"message": "I feel stuck", "mode": MentorSession.DEFAULT_MODE, "language": "en"},
        format="json",
    )

    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "session_id" in data
    assert data["mode"] == MentorSession.DEFAULT_MODE
    assert data["message"].startswith("Hello")

    messages = MentorMessage.objects.filter(session_id=data["session_id"]).order_by("created_at")
    assert messages.count() == 2
    assert messages.first().role == MentorMessage.Role.USER
    assert messages.last().role in (MentorMessage.Role.ASSISTANT, MentorMessage.Role.MENTOR)


@pytest.mark.django_db
def test_chat_async_enqueues_task():
    user = User.objects.create_user(email="async@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    class _Result:
        id = "task-123"

    with mock.patch("apps.mentor.tasks.mentor_chat_generate_task.apply_async", return_value=_Result()) as mocked:
        resp = client.post(
            "/api/v1/mentor/chat/?async=true",
            {"message": "I feel stuck", "mode": MentorSession.DEFAULT_MODE, "language": "en"},
            format="json",
        )

    assert resp.status_code == 202, resp.content
    data = resp.json()
    assert data["task_id"] == "task-123"
    mocked.assert_called_once()


@pytest.mark.django_db
def test_stream_requires_message_param():
    client = APIClient()
    user = User.objects.create_user(email="stream@example.com", password="testpass123")
    client.force_authenticate(user=user)

    resp = client.get("/api/v1/mentor/stream/")
    assert resp.status_code == 400
    assert resp["Content-Type"] == "text/event-stream"


@pytest.mark.django_db
def test_stream_returns_sse(monkeypatch):
    monkeypatch.setattr("apps.mentor.services.llm_client.requests.post", _mock_streaming_post)
    user = User.objects.create_user(email="stream2@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get("/api/v1/mentor/stream/", {"message": "hi there"})
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/event-stream"
    body = b"".join(resp.streaming_content)
    assert b"event" in body and b"token" in body
