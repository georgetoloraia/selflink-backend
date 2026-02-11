from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class ThreadMemberRole(models.TextChoices):
    MEMBER = "member", "Member"
    ADMIN = "admin", "Admin"


class MessageType(models.TextChoices):
    TEXT = "text", "Text"
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    SYSTEM = "system", "System"


class MessageStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    READ = "read", "Read"


class MessageAttachmentType(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"


class Thread(BaseModel):
    is_group = models.BooleanField(default=False)
    created_by = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="created_threads")
    title = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ThreadMember(BaseModel):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="thread_memberships")
    role = models.CharField(max_length=16, choices=ThreadMemberRole.choices, default=ThreadMemberRole.MEMBER)
    last_read_message = models.ForeignKey(
        "Message", on_delete=models.SET_NULL, related_name="readers", null=True, blank=True
    )

    class Meta:
        unique_together = ("thread", "user")


class Message(BaseModel):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="sent_messages")
    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )
    body = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=MessageType.choices, default=MessageType.TEXT)
    meta = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=MessageStatus.choices, default=MessageStatus.SENT)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    client_uuid = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ("thread", "client_uuid")


class MessageAttachment(BaseModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="messages/attachments/")
    type = models.CharField(max_length=8, choices=MessageAttachmentType.choices)
    mime_type = models.CharField(max_length=128)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class MessageReaction(BaseModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="message_reactions")
    emoji = models.CharField(max_length=16)

    class Meta:
        ordering = ["created_at"]
        unique_together = ("message", "user", "emoji")
