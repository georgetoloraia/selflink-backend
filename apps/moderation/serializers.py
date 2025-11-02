from __future__ import annotations

from rest_framework import serializers

from .models import Enforcement, Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "target_type",
            "target_id",
            "reason",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "status", "notes", "created_at"]

    def create(self, validated_data: dict) -> Report:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        report = Report.objects.create(reporter=user, **validated_data)
        return report


class EnforcementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enforcement
        fields = [
            "id",
            "target_type",
            "target_id",
            "action",
            "reason",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
