from __future__ import annotations

from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "created_at",
            "actor_user",
            "actor_ip",
            "action",
            "object_type",
            "object_id",
            "metadata",
            "hash_prev",
            "hash_self",
        ]
        read_only_fields = fields
