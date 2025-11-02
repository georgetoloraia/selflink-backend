from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Report(BaseModel):
    class TargetType(models.TextChoices):
        USER = "user", "User"
        POST = "post", "Post"
        COMMENT = "comment", "Comment"
        MESSAGE = "message", "Message"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In Review"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    reporter = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="reports_made")
    target_type = models.CharField(max_length=32, choices=TargetType.choices)
    target_id = models.BigIntegerField()
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)


class Enforcement(BaseModel):
    class Action(models.TextChoices):
        WARN = "warn", "Warn"
        SUSPEND = "suspend", "Suspend"
        BAN = "ban", "Ban"

    target_type = models.CharField(max_length=32, choices=Report.TargetType.choices)
    target_id = models.BigIntegerField()
    action = models.CharField(max_length=32, choices=Action.choices)
    reason = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
