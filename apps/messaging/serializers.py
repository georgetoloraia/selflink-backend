from __future__ import annotations

from typing import List

from django.db import transaction
from rest_framework import serializers

from apps.users.serializers import UserSerializer

from .models import Message, Thread, ThreadMember


class ThreadMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ThreadMember
        fields = ["id", "user", "role", "created_at", "updated_at"]
        read_only_fields = fields


class ThreadSerializer(serializers.ModelSerializer):
    members = ThreadMemberSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), write_only=True
    )

    class Meta:
        model = Thread
        fields = ["id", "is_group", "title", "members", "participant_ids", "created_at"]
        read_only_fields = ["id", "members", "created_at"]

    def validate_participant_ids(self, values: List[int]) -> List[int]:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if request.user.id in values:
                return values
            values.append(request.user.id)
        return list(dict.fromkeys(values))

    def create(self, validated_data: dict) -> Thread:
        participant_ids = validated_data.pop("participant_ids", [])
        request = self.context.get("request")
        user = request.user if request else None
        if not user or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        with transaction.atomic():
            thread = Thread.objects.create(created_by=user, **validated_data)
            member_ids = participant_ids or [user.id]
            for member_id in member_ids:
                ThreadMember.objects.create(thread=thread, user_id=member_id)
        return thread


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "thread", "sender", "body", "type", "meta", "created_at"]
        read_only_fields = ["id", "sender", "created_at"]

    def create(self, validated_data: dict) -> Message:
        request = self.context.get("request")
        user = request.user if request else None
        if not user or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        return Message.objects.create(sender=user, **validated_data)
