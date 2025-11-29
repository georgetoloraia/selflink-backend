from __future__ import annotations

from django.db import models
from apps.core.models import BaseModel


class MentorProfile(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="mentor_profile")
    tone = models.CharField(max_length=32, default="gentle")
    level = models.CharField(max_length=32, default="basic")
    preferences = models.JSONField(default=dict, blank=True)


class MentorSession(BaseModel):
    MODE_DEFAULT = "default"
    MODE_CHAT = "chat"
    MODE_DAILY = "daily"
    MODE_DAILY_MENTOR = "daily_mentor"
    MODE_NATAL_MENTOR = "natal_mentor"
    MODE_SOULMATCH = "soulmatch"
    DEFAULT_MODE = MODE_DAILY_MENTOR

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="mentor_sessions")
    mode = models.CharField(max_length=32, default=DEFAULT_MODE)
    language = models.CharField(max_length=8, default="en", blank=True, null=True)
    active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    question = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    sentiment = models.CharField(max_length=32, blank=True)
    date = models.DateField(blank=True, null=True)


class MentorMessage(BaseModel):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        MENTOR = "mentor", "Mentor"  # legacy alias

    session = models.ForeignKey(
        MentorSession,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    meta = models.JSONField(blank=True, null=True)

    def short_content(self) -> str:
        preview = (self.content or "")[:80]
        return f"{preview}..." if len(self.content or "") > 80 else preview


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
