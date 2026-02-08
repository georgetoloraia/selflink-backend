from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.community.models import Problem


@pytest.mark.django_db
def test_community_cors_preflight_allows_origin():
    problem = Problem.objects.create(title="CORS", description="")
    client = APIClient()
    resp = client.options(
        f"/api/v1/community/problems/{problem.id}/work/",
        HTTP_ORIGIN="https://community.self-link.com",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
    )
    assert resp.status_code in {200, 204}
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://community.self-link.com"
