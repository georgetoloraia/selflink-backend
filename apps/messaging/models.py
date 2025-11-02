from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Thread(BaseModel):
    is_group = models.BooleanField(default=False)
    created_by = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="created_threads")
    title = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ThreadMember(BaseModel):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        ADMIN = "admin", "Admin"

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="thread_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    last_read_message = models.ForeignKey(
        "Message", on_delete=models.SET_NULL, related_name="readers", null=True, blank=True
    )

    class Meta:
        unique_together = ("thread", "user")


class Message(BaseModel):
    class Type(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        SYSTEM = "system", "System"

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.TEXT)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
