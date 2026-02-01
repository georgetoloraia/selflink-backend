from __future__ import annotations

from datetime import date, time

from django.core.exceptions import FieldDoesNotExist
from rest_framework.test import APIClient

from apps.profile.models import UserProfile
from apps.users.models import Block, User
from apps.matching.views import _ordering_fields


def _create_user(email: str, handle: str, name: str) -> User:
    return User.objects.create_user(
        email=email,
        password="Pass12345!",
        handle=handle,
        name=name,
    )


def test_recommendations_compat_include_meta_returns_wrapper(db):
    user = _create_user("compat@example.com", "compat", "Compat User")
    user.birth_date = date(1990, 1, 1)
    user.birth_time = time(12, 0)
    user.birth_place = "Tbilisi"
    user.save()
    UserProfile.objects.create(user=user, gender="male", orientation="hetero", birth_city="Tbilisi")

    candidate = _create_user("candidate@example.com", "candidate", "Candidate User")
    UserProfile.objects.create(user=candidate, gender="female", orientation="hetero", birth_city="Tbilisi")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/soulmatch/recommendations/?include_meta=1")
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert "meta" in payload
    assert payload["meta"].get("mode") == "compat"


def test_recommendations_dating_missing_profile_fields_reason(db):
    user = _create_user("dating@example.com", "dating", "Dating User")
    user.birth_date = date(1991, 1, 1)
    user.birth_time = time(8, 30)
    user.birth_place = "Batumi"
    user.save()
    UserProfile.objects.create(user=user)

    candidate = _create_user("dating_candidate@example.com", "datingcand", "Dating Candidate")
    UserProfile.objects.create(user=candidate, gender="female", orientation="hetero", birth_city="Tbilisi")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/soulmatch/recommendations/?include_meta=1&mode=dating")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("meta", {}).get("reason") == "missing_profile_fields"
    assert "location" not in payload.get("meta", {}).get("missing_requirements", [])


def test_with_dating_includes_meta_eligibility(db):
    user = _create_user("with@example.com", "withuser", "With User")
    user.birth_date = date(1992, 2, 2)
    user.birth_time = time(6, 15)
    user.birth_place = "Kutaisi"
    user.save()
    UserProfile.objects.create(user=user)

    target = _create_user("target@example.com", "target", "Target User")
    UserProfile.objects.create(user=target, gender="female", orientation="hetero", birth_city="Tbilisi")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/api/v1/soulmatch/with/{target.id}/?mode=dating&include_meta=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("meta", {}).get("eligibility", {}).get("eligible") is False
    missing = payload.get("meta", {}).get("eligibility", {}).get("missing_requirements", [])
    assert "gender" in missing or "orientation" in missing


def test_with_returns_404_for_blocked_target(db):
    user = _create_user("blocker@example.com", "blocker", "Blocker")
    target = _create_user("blocked@example.com", "blocked", "Blocked")
    UserProfile.objects.create(user=user, gender="male", orientation="hetero", birth_city="Tbilisi")
    UserProfile.objects.create(user=target, gender="female", orientation="hetero", birth_city="Tbilisi")
    Block.objects.create(user=user, target=target)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/api/v1/soulmatch/with/{target.id}/?mode=compat")
    assert response.status_code == 404


def test_ordering_fields_fallback(monkeypatch):
    original_get_field = User._meta.get_field

    def get_field(name):
        if name in {"created_at", "date_joined"}:
            raise FieldDoesNotExist
        return original_get_field(name)

    monkeypatch.setattr(User._meta, "get_field", get_field)
    assert _ordering_fields(User) == ["id"]
