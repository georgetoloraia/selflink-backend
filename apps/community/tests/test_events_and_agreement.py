from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.community.models import Problem, ProblemEvent
from apps.users.models import User


@pytest.mark.django_db
def test_agreement_get_always_returns_agreement():
    problem = Problem.objects.create(title="Problem", description="desc")
    client = APIClient()
    resp = client.get(f"/api/v1/community/problems/{problem.id}/agreement/")
    assert resp.status_code == 200
    payload = resp.json()
    agreement = payload.get("agreement")
    assert agreement is not None
    assert agreement["license_spdx"] == "MIT"
    assert agreement.get("version")
    assert agreement.get("text")
    assert agreement.get("is_active") is True


@pytest.mark.django_db
def test_agreement_accept_emits_event():
    user = User.objects.create_user(
        email="agree@example.com",
        password="pass1234",
        handle="agree",
        name="Agree",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(f"/api/v1/community/problems/{problem.id}/agreement/accept/")
    assert resp.status_code == 200
    assert ProblemEvent.objects.filter(problem=problem, type="problem.agreement_accepted").exists()


@pytest.mark.django_db
def test_create_problem_emits_event_and_sets_last_activity():
    user = User.objects.create_user(
        email="creator2@example.com",
        password="pass1234",
        handle="creator2",
        name="Creator Two",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/v1/community/problems/",
        {"title": "New problem", "description": "desc"},
        format="json",
    )
    assert resp.status_code == 201
    problem_id = resp.json()["id"]
    problem = Problem.objects.get(pk=problem_id)
    assert problem.last_activity_at is not None
    assert ProblemEvent.objects.filter(problem=problem, type="problem.created").exists()


@pytest.mark.django_db
def test_retrieve_increments_views_count():
    problem = Problem.objects.create(title="Problem", description="desc")
    client = APIClient()

    resp_one = client.get(f"/api/v1/community/problems/{problem.id}/")
    assert resp_one.status_code == 200
    resp_two = client.get(f"/api/v1/community/problems/{problem.id}/")
    assert resp_two.status_code == 200

    problem.refresh_from_db()
    assert problem.views_count >= 2


@pytest.mark.django_db
def test_events_endpoint_shape():
    problem = Problem.objects.create(title="Problem", description="desc")
    ProblemEvent.objects.create(problem=problem, actor=None, type="problem.created", metadata={})

    client = APIClient()
    resp = client.get(f"/api/v1/community/problems/{problem.id}/events/")
    assert resp.status_code == 200
    data = resp.json()
    items = data["results"] if isinstance(data, dict) and "results" in data else data
    assert items
    first = items[0]
    assert set(first.keys()) == {"id", "type", "created_at", "actor", "metadata"}
