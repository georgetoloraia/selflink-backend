from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.community.models import Problem


@pytest.mark.django_db
def test_summary_cache_headers():
    client = APIClient()
    resp = client.get("/api/v1/community/summary/")
    assert resp.status_code == 200
    cache_control = resp.headers.get("Cache-Control", "")
    assert "no-store" in cache_control


@pytest.mark.django_db
def test_problems_cache_headers():
    problem = Problem.objects.create(title="Problem", description="desc")
    client = APIClient()
    list_resp = client.get("/api/v1/community/problems/")
    assert list_resp.status_code == 200
    assert "no-store" in list_resp.headers.get("Cache-Control", "")

    detail_resp = client.get(f"/api/v1/community/problems/{problem.id}/")
    assert detail_resp.status_code == 200
    assert "no-store" in detail_resp.headers.get("Cache-Control", "")
