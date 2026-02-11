from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class ReportTargetType(models.TextChoices):
    USER = "user", "User"
    POST = "post", "Post"
    COMMENT = "comment", "Comment"
    MESSAGE = "message", "Message"


class ReportStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_REVIEW = "in_review", "In Review"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class EnforcementAction(models.TextChoices):
    WARN = "warn", "Warn"
    SUSPEND = "suspend", "Suspend"
    BAN = "ban", "Ban"


class Report(BaseModel):
    reporter = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="reports_made")
    target_type = models.CharField(max_length=32, choices=ReportTargetType.choices)
    target_id = models.BigIntegerField()
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=ReportStatus.choices, default=ReportStatus.OPEN)
    notes = models.TextField(blank=True)


class Enforcement(BaseModel):
    target_type = models.CharField(max_length=32, choices=ReportTargetType.choices)
    target_id = models.BigIntegerField()
    action = models.CharField(max_length=32, choices=EnforcementAction.choices)
    reason = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
