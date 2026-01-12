from __future__ import annotations

from unittest import mock

import pytest

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.mark.django_db
@override_settings(RATE_LIMITS_ENABLED=True, MENTOR_RPS_USER=1, MENTOR_RPS_GLOBAL=1)
def test_mentor_rate_limit_returns_429():
    cache.clear()
    user = User.objects.create_user(email="limit@example.com", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)

    with mock.patch("apps.mentor.api.full_completion", return_value="Hello"):
        first = client.post("/api/v1/mentor/chat/", {"message": "hello"}, format="json")
        second = client.post("/api/v1/mentor/chat/", {"message": "hello again"}, format="json")

    assert first.status_code == 202
    assert second.status_code == 429
