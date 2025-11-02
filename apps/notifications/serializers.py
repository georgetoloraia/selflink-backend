from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "payload", "is_read", "created_at", "read_at"]
        read_only_fields = ["id", "created_at", "read_at"]

    def update(self, instance: Notification, validated_data: dict) -> Notification:
        is_read = validated_data.get("is_read")
        if is_read and not instance.is_read:
            instance.is_read = True
            instance.read_at = timezone.now()
            instance.save(update_fields=["is_read", "read_at"])
        return instance
