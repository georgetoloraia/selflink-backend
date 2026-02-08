from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.community.models import Problem, ProblemComment, WorkArtifact
from apps.users.models import User


@pytest.mark.django_db
def test_problems_list_contract_shape():
    user = User.objects.create_user(
        email="shape_list@example.com",
        password="pass1234",
        handle="shape_list",
        name="Shape List",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    ProblemComment.objects.create(problem=problem, user=user, body="hi")
    WorkArtifact.objects.create(problem=problem, user=user, title="Art", description="", url="")

    client = APIClient()
    resp = client.get("/api/v1/community/problems/")
    assert resp.status_code == 200
    payload = resp.json()
    items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
    assert isinstance(items, list)
    row = next(item for item in items if item["id"] == problem.id)
    required = {
        "id",
        "title",
        "description",
        "status",
        "created_at",
        "comments_count",
        "likes_count",
        "artifacts_count",
        "working_count",
        "has_liked",
        "is_working",
    }
    assert required.issubset(row.keys())


@pytest.mark.django_db
def test_problem_detail_contract_shape_includes_working_on_this():
    problem = Problem.objects.create(title="Problem", description="desc")

    client = APIClient()
    resp = client.get(f"/api/v1/community/problems/{problem.id}/")
    assert resp.status_code == 200
    data = resp.json()
    required = {
        "id",
        "title",
        "description",
        "status",
        "created_at",
        "comments_count",
        "likes_count",
        "artifacts_count",
        "working_count",
        "has_liked",
        "is_working",
        "working_on_this",
    }
    assert required.issubset(data.keys())
    assert isinstance(data["working_on_this"], list)


@pytest.mark.django_db
def test_problem_comments_contract_shape():
    user = User.objects.create_user(
        email="shape_comments@example.com",
        password="pass1234",
        handle="shape_comments",
        name="Shape Comments",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    ProblemComment.objects.create(problem=problem, user=user, body="hi")

    client = APIClient()
    resp = client.get(f"/api/v1/community/problems/{problem.id}/comments/")
    assert resp.status_code == 200
    payload = resp.json()
    items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
    assert isinstance(items, list)
    row = items[0]
    required = {"id", "body", "created_at", "user", "likes_count", "has_liked"}
    assert required.issubset(row.keys())
    assert {"id", "username", "avatar_url"}.issubset(row["user"].keys())


@pytest.mark.django_db
def test_problem_artifacts_contract_shape():
    user = User.objects.create_user(
        email="shape_artifacts@example.com",
        password="pass1234",
        handle="shape_artifacts",
        name="Shape Artifacts",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    WorkArtifact.objects.create(problem=problem, user=user, title="Art", description="", url="")

    client = APIClient()
    resp = client.get(f"/api/v1/community/problems/{problem.id}/artifacts/")
    assert resp.status_code == 200
    payload = resp.json()
    items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
    assert isinstance(items, list)
    row = items[0]
    required = {"id", "title", "description", "url", "created_at", "user"}
    assert required.issubset(row.keys())
    assert {"id", "username", "avatar_url"}.issubset(row["user"].keys())


@pytest.mark.django_db
def test_artifact_comments_contract_shape():
    user = User.objects.create_user(
        email="shape_artifact_comments@example.com",
        password="pass1234",
        handle="shape_artifact_comments",
        name="Shape Artifact Comments",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    artifact = WorkArtifact.objects.create(problem=problem, user=user, title="Art", description="", url="")

    client = APIClient()
    resp = client.get(f"/api/v1/community/artifacts/{artifact.id}/comments/")
    assert resp.status_code == 200
    payload = resp.json()
    items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
    assert isinstance(items, list)
    if items:
        row = items[0]
        required = {"id", "body", "created_at", "user"}
        assert required.issubset(row.keys())
        assert {"id", "username", "avatar_url"}.issubset(row["user"].keys())
