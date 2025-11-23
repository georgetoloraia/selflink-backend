import pytest
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.mentor.models import MentorMessage, MentorSession
from apps.users.models import User


def _extract_results(data):
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
def test_daily_entry_requires_auth():
    client = APIClient()
    resp = client.post("/api/v1/mentor/daily/entry/", {"text": "hello"}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_daily_entry_creates_session_and_messages():
    user = User.objects.create_user(email="daily@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/v1/mentor/daily/entry/",
        {"text": "Today I felt grateful for my friends."},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["reply"]

    session = MentorSession.objects.get(id=data["session_id"])
    assert session.mode == MentorSession.MODE_DAILY
    assert MentorMessage.objects.filter(session=session).count() == 2


@pytest.mark.django_db
def test_daily_history_respects_limit():
    user = User.objects.create_user(email="history@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    today = timezone.localdate()
    for i in range(3):
        date_str = (today - timedelta(days=i)).isoformat()
        client.post(
            "/api/v1/mentor/daily/entry/",
            {"text": f"Entry {i}", "date": date_str},
            format="json",
        )

    resp = client.get("/api/v1/mentor/daily/history/", {"limit": 2})
    assert resp.status_code == 200, resp.content
    payload = resp.json()
    results = _extract_results(payload)
    assert isinstance(results, list)
    assert len(results) == 2
