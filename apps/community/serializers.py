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
    comments_count = serializers.IntegerField(read_only=True)
    artifacts_count = serializers.IntegerField(read_only=True)
    working_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Problem
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "comments_count",
            "artifacts_count",
            "working_count",
        ]
        read_only_fields = ["id", "created_at", "comments_count", "artifacts_count", "working_count"]

    def create(self, validated_data: dict) -> Problem:
        validated_data.setdefault("description", "")
        validated_data.setdefault("is_active", True)
        return Problem.objects.create(**validated_data)


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


class MoneySerializer(serializers.Serializer):
    amount = serializers.CharField()
    currency = serializers.CharField()


class ContributorsSerializer(serializers.Serializer):
    count = serializers.IntegerField()


class DistributionItemSerializer(serializers.Serializer):
    user = UserTinySerializer()
    amount = serializers.CharField()
    currency = serializers.CharField()


class CommunitySummarySerializer(serializers.Serializer):
    as_of = serializers.DateTimeField()
    total_income = MoneySerializer()
    contributors_reward = MoneySerializer()
    contributors = ContributorsSerializer()
    distribution_preview = DistributionItemSerializer(many=True)
