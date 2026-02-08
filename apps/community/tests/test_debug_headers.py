from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_debug_headers_present_for_community_routes():
    client = APIClient()

    resp = client.get("/api/v1/community/problems/")
    assert resp.status_code == 200
    assert "X-SL-Instance" in resp.headers
    assert "X-SL-DB" in resp.headers
    assert "X-SL-Commit" in resp.headers

    resp = client.get("/api/v1/community/summary/")
    assert resp.status_code == 200
    assert "X-SL-Instance" in resp.headers
    assert "X-SL-DB" in resp.headers
    assert "X-SL-Commit" in resp.headers
