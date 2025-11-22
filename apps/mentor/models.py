from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class MentorProfile(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="mentor_profile")
    tone = models.CharField(max_length=32, default="gentle")
    level = models.CharField(max_length=32, default="basic")
    preferences = models.JSONField(default=dict, blank=True)


class MentorSession(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="mentor_sessions")
    question = models.TextField()
    answer = models.TextField()
    sentiment = models.CharField(max_length=32, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    mode = models.CharField(max_length=32, default="default")
    language = models.CharField(max_length=8, blank=True, null=True)
    active = models.BooleanField(default=True)


class MentorMessage(BaseModel):
    class Role(models.TextChoices):
        USER = "user", "User"
        MENTOR = "mentor", "Mentor"

    session = models.ForeignKey(
        MentorSession,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    meta = models.JSONField(blank=True, null=True)


class DailyTask(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="daily_tasks")
    task = models.CharField(max_length=255)
    due_date = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)


class MentorMemory(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="mentor_memory")
    notes = models.JSONField(default=dict, blank=True)
    last_summary = models.TextField(blank=True)

    class Meta:
        verbose_name = "Mentor Memory"
        verbose_name_plural = "Mentor Memories"
