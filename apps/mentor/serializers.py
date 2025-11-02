from __future__ import annotations

from datetime import date

from django.utils import timezone
from rest_framework import serializers

from .models import DailyTask, MentorProfile, MentorSession


class MentorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorProfile
        fields = ["tone", "level", "preferences"]


class MentorSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorSession
        fields = ["id", "question", "answer", "sentiment", "created_at"]
        read_only_fields = fields


class MentorAskSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2048)


class DailyTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTask
        fields = ["id", "task", "due_date", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_due_date(self, value: date) -> date:
        if value < timezone.localdate():
            raise serializers.ValidationError("Due date cannot be in the past")
        return value
