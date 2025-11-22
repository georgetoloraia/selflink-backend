import pytest
from rest_framework.test import APIClient

from apps.users.models import User


def _extract_results(data):
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
def test_mentor_chat_requires_auth():
    client = APIClient()
    resp = client.post(
        "/api/v1/mentor/chat/",
        {"message": "hi", "mode": "default", "language": "en"},
        format="json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_mentor_chat_returns_reply_for_authenticated_user():
    user = User.objects.create_user(email="test@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/v1/mentor/chat/",
        {"message": "I feel stuck", "mode": "default", "language": "en"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "mentor_reply" in data
    assert data["mode"] == "default"


@pytest.mark.django_db
def test_mentor_history_returns_list():
    user = User.objects.create_user(email="test2@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    client.post(
        "/api/v1/mentor/chat/",
        {"message": "hello", "mode": "default", "language": "en"},
        format="json",
    )

    resp = client.get("/api/v1/mentor/history/")
    assert resp.status_code == 200
    payload = resp.json()
    results = _extract_results(payload)
    assert isinstance(results, list)
    assert len(results) >= 1
