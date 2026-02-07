from __future__ import annotations

from typing import Optional

from django.db.models import QuerySet
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import AgreementAcceptance, Problem, ProblemAgreement, WorkArtifact


class AgreementAcceptedForProblem(BasePermission):
    """
    Require an active agreement and a user acceptance for all participation actions.
    """

    message = "AGREEMENT_REQUIRED"

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True

        problem = self._resolve_problem(request, view)
        if problem is None:
            return False

        agreement = (
            ProblemAgreement.objects.filter(problem=problem, is_active=True)
            .only("id", "problem_id")
            .first()
        )
        if agreement is None:
            return False

        return AgreementAcceptance.objects.filter(
            problem=problem,
            agreement=agreement,
            user=request.user,
        ).exists()

    def _resolve_problem(self, request, view) -> Optional[Problem]:
        if not hasattr(view, "basename"):
            return None

        if (
            view.basename == "community-artifacts"
            and getattr(view, "action", None) == "comments"
        ):
            artifact_id = view.kwargs.get("pk")
            if not artifact_id:
                return None
            artifact = (
                WorkArtifact.objects.select_related("problem")
                .only("id", "problem_id")
                .filter(pk=artifact_id)
                .first()
            )
            return artifact.problem if artifact else None

        if view.basename == "community-problems":
            problem_id = view.kwargs.get("pk")
            if not problem_id:
                return None
            return Problem.objects.only("id").filter(pk=problem_id).first()

        return None
