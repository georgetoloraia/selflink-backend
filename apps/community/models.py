from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Problem(BaseModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, default="open", db_index=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"Problem<{self.id}>"


class ProblemAgreement(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="agreements")
    text = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"ProblemAgreement<{self.id}>"


class AgreementAcceptance(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="agreement_acceptances")
    agreement = models.ForeignKey(
        ProblemAgreement, on_delete=models.CASCADE, related_name="acceptances"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="problem_acceptances")
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "agreement")

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"AgreementAcceptance<{self.id}>"


class ProblemWork(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="work_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="problem_work")
    status = models.CharField(max_length=32, default="marked")
    note = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"ProblemWork<{self.id}>"


class WorkArtifact(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="artifacts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artifacts")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"WorkArtifact<{self.id}>"


class ProblemComment(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="problem_comments")
    body = models.TextField()

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"ProblemComment<{self.id}>"


class ArtifactComment(BaseModel):
    artifact = models.ForeignKey(WorkArtifact, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artifact_comments")
    body = models.TextField()


class ProblemLike(BaseModel):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="problem_likes")

    class Meta:
        unique_together = ("problem", "user")


class ProblemCommentLike(BaseModel):
    comment = models.ForeignKey(ProblemComment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="problem_comment_likes",
    )

    class Meta:
        unique_together = ("comment", "user")

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"ArtifactComment<{self.id}>"
