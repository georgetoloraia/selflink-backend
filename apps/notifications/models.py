from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
