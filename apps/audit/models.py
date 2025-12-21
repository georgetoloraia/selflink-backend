from __future__ import annotations

import hashlib
import json
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    actor_ip = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=128)
    object_type = models.CharField(max_length=128)
    object_id = models.CharField(max_length=128)
    metadata = models.JSONField(default=dict, blank=True)
    hash_prev = models.CharField(max_length=64, blank=True)
    hash_self = models.CharField(max_length=64, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def save(self, *args, **kwargs) -> None:  # type: ignore[override]
        if not self._state.adding:
            raise ValidationError("AuditEvent rows are append-only.")

        if not self.created_at:
            self.created_at = timezone.now()

        with transaction.atomic():
            if not self.hash_prev:
                last_event = AuditEvent.objects.select_for_update().order_by("-created_at", "-id").first()
                self.hash_prev = last_event.hash_self if last_event else ""

            self.hash_self = self._compute_hash()
            super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        raise ValidationError("AuditEvent rows are append-only.")

    def _compute_hash(self) -> str:
        payload = {
            "prev": self.hash_prev or "",
            "created_at": self.created_at.isoformat(),
            "actor_user_id": str(self.actor_user_id or ""),
            "action": self.action,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "metadata": self.metadata or {},
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
