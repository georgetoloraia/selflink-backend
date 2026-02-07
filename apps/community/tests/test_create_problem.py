from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.mark.django_db
def test_create_problem_requires_auth():
    client = APIClient()
    resp = client.post(
        "/api/v1/community/problems/",
        {"title": "Test problem", "description": "desc"},
        format="json",
    )
    assert resp.status_code in {401, 403}


@pytest.mark.django_db
def test_create_problem_success_and_list_public():
    user = User.objects.create_user(
        email="creator@example.com",
        password="pass1234",
        handle="creator",
        name="Creator",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/v1/community/problems/",
        {"title": "Test problem", "description": "desc"},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test problem"
    assert "id" in data

    client.force_authenticate(user=None)
    list_resp = client.get("/api/v1/community/problems/")
    assert list_resp.status_code == 200
