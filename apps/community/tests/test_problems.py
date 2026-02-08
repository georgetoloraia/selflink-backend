from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.community.models import (
    AgreementAcceptance,
    Problem,
    ProblemAgreement,
    ProblemComment,
    ProblemCommentLike,
    ProblemLike,
    ProblemWork,
    WorkArtifact,
)
from apps.users.models import User


@pytest.mark.django_db
def test_problem_list_includes_counts():
    user = User.objects.create_user(
        email="counts@example.com",
        password="pass1234",
        handle="counts",
        name="Counts",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    ProblemComment.objects.create(problem=problem, user=user, body="hi")
    WorkArtifact.objects.create(problem=problem, user=user, title="Art", description="", url="")
    ProblemWork.objects.create(problem=problem, user=user, status="marked", note="")
    ProblemLike.objects.create(problem=problem, user=user)

    client = APIClient()
    resp = client.get("/api/v1/community/problems/")
    assert resp.status_code == 200
    data = resp.json()
    items = data["results"] if isinstance(data, dict) and "results" in data else data
    assert isinstance(items, list)
    row = next(item for item in items if item["id"] == problem.id)
    assert isinstance(row["comments_count"], int)
    assert isinstance(row["likes_count"], int)
    assert isinstance(row["artifacts_count"], int)
    assert isinstance(row["working_count"], int)
    assert row["has_liked"] is False
    assert row["is_working"] is False


@pytest.mark.django_db
def test_work_is_idempotent_and_unwork():
    user = User.objects.create_user(
        email="work@example.com",
        password="pass1234",
        handle="work",
        name="Work",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    agreement = ProblemAgreement.objects.create(problem=problem, text="MIT", is_active=True)
    AgreementAcceptance.objects.create(problem=problem, agreement=agreement, user=user)

    client = APIClient()
    client.force_authenticate(user=user)

    resp_one = client.post(
        f"/api/v1/community/problems/{problem.id}/work/",
        {"status": "marked", "note": ""},
        format="json",
    )
    assert resp_one.status_code in {200, 201}
    assert resp_one.json()["is_working"] is True
    resp_two = client.post(
        f"/api/v1/community/problems/{problem.id}/work/",
        {"status": "marked", "note": ""},
        format="json",
    )
    assert resp_two.status_code in {200, 201}
    assert ProblemWork.objects.filter(problem=problem, user=user).count() == 1

    resp_delete = client.delete(f"/api/v1/community/problems/{problem.id}/work/")
    assert resp_delete.status_code == 200
    assert resp_delete.json()["is_working"] is False
    assert ProblemWork.objects.filter(problem=problem, user=user).count() == 0


@pytest.mark.django_db
def test_problem_like_and_comment_like():
    user = User.objects.create_user(
        email="likes@example.com",
        password="pass1234",
        handle="likes",
        name="Likes",
    )
    problem = Problem.objects.create(title="Problem", description="desc")
    agreement = ProblemAgreement.objects.create(problem=problem, text="MIT", is_active=True)
    AgreementAcceptance.objects.create(problem=problem, agreement=agreement, user=user)
    comment = ProblemComment.objects.create(problem=problem, user=user, body="hi")

    client = APIClient()
    client.force_authenticate(user=user)

    like_resp = client.post(f"/api/v1/community/problems/{problem.id}/like/")
    assert like_resp.status_code == 200
    assert like_resp.json()["has_liked"] is True
    assert ProblemLike.objects.filter(problem=problem, user=user).count() == 1

    unlike_resp = client.delete(f"/api/v1/community/problems/{problem.id}/like/")
    assert unlike_resp.status_code == 200
    assert unlike_resp.json()["has_liked"] is False

    comment_like = client.post(
        f"/api/v1/community/problems/{problem.id}/comments/{comment.id}/like/"
    )
    assert comment_like.status_code == 200
    assert comment_like.json()["has_liked"] is True
    assert ProblemCommentLike.objects.filter(comment=comment, user=user).count() == 1
