from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AgreementAcceptance,
    ArtifactComment,
    Problem,
    ProblemAgreement,
    ProblemComment,
    ProblemWork,
    WorkArtifact,
)

User = get_user_model()


class UserTinySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="handle", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "avatar_url"]

    def get_avatar_url(self, obj: User) -> str | None:
        return getattr(obj, "photo", None) or None


class ProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ["id", "title", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProblemAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemAgreement
        fields = ["id", "text", "is_active"]
        read_only_fields = fields


class AgreementAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgreementAcceptance
        fields = ["id", "problem", "agreement", "accepted_at"]
        read_only_fields = fields


class ProblemWorkSerializer(serializers.ModelSerializer):
    user = UserTinySerializer(read_only=True)

    class Meta:
        model = ProblemWork
        fields = ["id", "status", "note", "created_at", "user"]
        read_only_fields = ["id", "created_at", "user"]


class WorkArtifactSerializer(serializers.ModelSerializer):
    user = UserTinySerializer(read_only=True)

    class Meta:
        model = WorkArtifact
        fields = ["id", "title", "description", "url", "created_at", "user"]
        read_only_fields = ["id", "created_at", "user"]


class ProblemCommentSerializer(serializers.ModelSerializer):
    user = UserTinySerializer(read_only=True)

    class Meta:
        model = ProblemComment
        fields = ["id", "body", "created_at", "user"]
        read_only_fields = ["id", "created_at", "user"]


class ArtifactCommentSerializer(serializers.ModelSerializer):
    user = UserTinySerializer(read_only=True)

    class Meta:
        model = ArtifactComment
        fields = ["id", "body", "created_at", "user"]
        read_only_fields = ["id", "created_at", "user"]


class CommunityLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class CommunityLoginResponseSerializer(serializers.Serializer):
    token_type = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserTinySerializer()


class CommunityMeSerializer(serializers.Serializer):
    user = UserTinySerializer()


class CommunityLogoutSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
