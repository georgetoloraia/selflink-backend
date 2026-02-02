from __future__ import annotations

from datetime import date, time

import pytest
from rest_framework.test import APIClient

from apps.profile.models import UserProfile
from apps.users.models import User
import apps.matching.views as matching_views


def _create_user(email: str, handle: str, name: str) -> User:
    return User.objects.create_user(
        email=email,
        password="Pass12345!",
        handle=handle,
        name=name,
    )


@pytest.mark.django_db
def test_soulmatch_with_contract_sync(monkeypatch):
    monkeypatch.setattr(matching_views, "should_run_async", lambda request: False)

    user = _create_user("u1@example.com", "u1", "User One")
    user.birth_date = date(1990, 1, 1)
    user.birth_time = time(9, 0)
    user.birth_place = "Tbilisi"
    user.save()
    UserProfile.objects.create(user=user, gender="male", orientation="hetero", birth_city="Tbilisi")

    target = _create_user("u2@example.com", "u2", "User Two")
    UserProfile.objects.create(user=target, gender="female", orientation="hetero", birth_city="Tbilisi")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/api/v1/soulmatch/with/{target.id}/?include_meta=1&mode=compat")
    assert response.status_code == 200
    payload = response.json()

    user_obj = payload.get("user", {})
    assert {"id", "handle", "name", "photo"} <= set(user_obj.keys())
    assert isinstance(payload.get("user_id"), int)
    assert isinstance(payload.get("score"), int)
    components = payload.get("components", {})
    assert {"astro", "matrix", "psychology", "lifestyle"} <= set(components.keys())
    assert isinstance(payload.get("tags"), list)

    meta = payload.get("meta", {})
    assert meta.get("mode") == "compat"
    assert "eligibility" in meta


@pytest.mark.django_db
def test_soulmatch_recommendations_contract(monkeypatch):
    monkeypatch.setattr(matching_views, "should_run_async", lambda request: False)

    user = _create_user("r1@example.com", "r1", "Reco User")
    user.birth_date = date(1991, 2, 2)
    user.birth_time = time(8, 30)
    user.birth_place = "Batumi"
    user.save()
    UserProfile.objects.create(user=user, gender="male", orientation="hetero", birth_city="Batumi")

    candidate = _create_user("r2@example.com", "r2", "Reco Candidate")
    UserProfile.objects.create(user=candidate, gender="female", orientation="hetero", birth_city="Tbilisi")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/soulmatch/recommendations/?include_meta=1&mode=compat")
    assert response.status_code == 200
    payload = response.json()

    assert set(payload.keys()) >= {"results", "meta"}
    meta = payload.get("meta", {})
    assert {"mode", "reason", "missing_requirements", "candidate_count"} <= set(meta.keys())

    allowed_reasons = {
        None,
        "missing_birth_data",
        "missing_profile_fields",
        "no_candidates",
        "no_results",
    }
    assert meta.get("reason") in allowed_reasons

    results = payload.get("results", [])
    for item in results:
        user_obj = item.get("user", {})
        assert {"id", "handle", "name", "photo"} <= set(user_obj.keys())
        assert isinstance(item.get("score"), int)
        components = item.get("components", {})
        assert {"astro", "matrix", "psychology", "lifestyle"} <= set(components.keys())
        assert isinstance(item.get("tags"), list)
