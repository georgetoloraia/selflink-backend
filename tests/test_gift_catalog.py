from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
@override_settings(FEATURE_FLAGS={"payments": True})
def test_gift_catalog_includes_seeded_test_gift() -> None:
    client = APIClient()
    response = client.get("/api/v1/payments/gifts/")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    test_gift = next((gift for gift in results if gift.get("key") == "test_heart_1usd"), None)
    assert test_gift is not None
    assert test_gift.get("price_cents") == 100
    assert test_gift.get("price_slc_cents") == 100
