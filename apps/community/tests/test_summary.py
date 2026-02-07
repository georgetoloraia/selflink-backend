from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_community_summary_shape():
    client = APIClient()
    resp = client.get("/api/v1/community/summary/")
    assert resp.status_code == 200
    data = resp.json()

    assert set(data.keys()) == {
        "as_of",
        "total_income",
        "contributors_reward",
        "contributors",
        "distribution_preview",
    }
    assert isinstance(data["as_of"], str)
    assert isinstance(data["total_income"]["amount"], str)
    assert isinstance(data["total_income"]["currency"], str)
    assert isinstance(data["contributors_reward"]["amount"], str)
    assert isinstance(data["contributors_reward"]["currency"], str)
    assert isinstance(data["contributors"]["count"], int)
    assert isinstance(data["distribution_preview"], list)
