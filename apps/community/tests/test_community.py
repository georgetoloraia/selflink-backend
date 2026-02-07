from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.community.models import (
    AgreementAcceptance,
    Problem,
    ProblemAgreement,
    WorkArtifact,
)
from apps.users.models import User


@pytest.mark.django_db
def test_post_problem_comment_requires_agreement():
    user = User.objects.create_user(
        email="commenter@example.com",
        password="pass1234",
        handle="commenter",
        name="Commenter",
    )
    problem = Problem.objects.create(title="Test Problem", description="desc")
    agreement = ProblemAgreement.objects.create(problem=problem, text="MIT", is_active=True)

    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        f"/api/v1/community/problems/{problem.id}/comments/",
        {"body": "Hello"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.json() == {"detail": "AGREEMENT_REQUIRED"}

    AgreementAcceptance.objects.create(problem=problem, agreement=agreement, user=user)

    resp = client.post(
        f"/api/v1/community/problems/{problem.id}/comments/",
        {"body": "Hello"},
        format="json",
    )
    assert resp.status_code == 201


@pytest.mark.django_db
def test_post_artifact_comment_requires_agreement():
    user = User.objects.create_user(
        email="artifact_commenter@example.com",
        password="pass1234",
        handle="artifact_commenter",
        name="Artifact Commenter",
    )
    problem = Problem.objects.create(title="Test Problem", description="desc")
    agreement = ProblemAgreement.objects.create(problem=problem, text="MIT", is_active=True)
    artifact = WorkArtifact.objects.create(
        problem=problem,
        user=user,
        title="Artifact",
        description="",
        url="",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        f"/api/v1/community/artifacts/{artifact.id}/comments/",
        {"body": "Nice work"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.json() == {"detail": "AGREEMENT_REQUIRED"}

    AgreementAcceptance.objects.create(problem=problem, agreement=agreement, user=user)

    resp = client.post(
        f"/api/v1/community/artifacts/{artifact.id}/comments/",
        {"body": "Nice work"},
        format="json",
    )
    assert resp.status_code == 201


@pytest.mark.django_db
def test_login_success_returns_token_shape():
    user = User.objects.create_user(
        email="login@example.com",
        password="pass1234",
        handle="login",
        name="Login User",
    )

    client = APIClient()
    resp = client.post(
        "/api/v1/community/auth/login/",
        {"username": user.email, "password": "pass1234"},
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "Bearer"
    assert isinstance(data.get("access"), str) and data["access"]
    assert isinstance(data.get("refresh"), str) and data["refresh"]
    assert data["user"]["id"] == user.id
    assert data["user"]["username"] == user.handle
    assert "avatar_url" in data["user"]


@pytest.mark.django_db
def test_login_invalid_credentials():
    user = User.objects.create_user(
        email="badlogin@example.com",
        password="pass1234",
        handle="badlogin",
        name="Bad Login",
    )

    client = APIClient()
    resp = client.post(
        "/api/v1/community/auth/login/",
        {"username": user.email, "password": "wrongpass"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "INVALID_CREDENTIALS"}
