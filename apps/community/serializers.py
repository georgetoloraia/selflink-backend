from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AgreementAcceptance,
    ArtifactComment,
    Problem,
    ProblemAgreement,
    ProblemComment,
    ProblemEvent,
    ProblemWork,
    WorkArtifact,
)

User = get_user_model()


class StringIDModelSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)


class UserTinySerializer(StringIDModelSerializer):
    username = serializers.CharField(source="handle", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "avatar_url"]

    def get_avatar_url(self, obj: User) -> str | None:
        return getattr(obj, "photo", None) or None


class ProblemSerializer(StringIDModelSerializer):
    status = serializers.CharField(read_only=True)
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    artifacts_count = serializers.SerializerMethodField()
    working_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()
    is_working = serializers.SerializerMethodField()
    working_on_this = serializers.SerializerMethodField()
    views_count = serializers.IntegerField(read_only=True)
    last_activity_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Problem
        fields = [
            "id",
            "title",
            "description",
            "status",
            "created_at",
            "comments_count",
            "likes_count",
            "artifacts_count",
            "working_count",
            "has_liked",
            "is_working",
            "working_on_this",
            "views_count",
            "last_activity_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "status",
            "comments_count",
            "likes_count",
            "artifacts_count",
            "working_count",
            "has_liked",
            "is_working",
            "working_on_this",
            "views_count",
            "last_activity_at",
        ]

    def create(self, validated_data: dict) -> Problem:
        validated_data.setdefault("description", "")
        validated_data.setdefault("is_active", True)
        return Problem.objects.create(**validated_data)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.context.get("include_working_on_this"):
            self.fields.pop("working_on_this", None)

    def get_working_on_this(self, obj: Problem) -> list[dict]:
        users = self.context.get("working_users") or []
        return UserTinySerializer(users, many=True, context=self.context).data

    def _get_int(self, obj: Problem, attr: str) -> int:
        value = getattr(obj, attr, None)
        return int(value or 0)

    def _get_bool(self, obj: Problem, attr: str) -> bool:
        value = getattr(obj, attr, None)
        return bool(value)

    def get_comments_count(self, obj: Problem) -> int:
        return self._get_int(obj, "comments_count")

    def get_likes_count(self, obj: Problem) -> int:
        return self._get_int(obj, "likes_count")

    def get_artifacts_count(self, obj: Problem) -> int:
        return self._get_int(obj, "artifacts_count")

    def get_working_count(self, obj: Problem) -> int:
        return self._get_int(obj, "working_count")

    def get_has_liked(self, obj: Problem) -> bool:
        return self._get_bool(obj, "has_liked")

    def get_is_working(self, obj: Problem) -> bool:
        return self._get_bool(obj, "is_working")


class ProblemAgreementSerializer(StringIDModelSerializer):
    class Meta:
        model = ProblemAgreement
        fields = ["id", "license_spdx", "version", "text", "is_active"]
        read_only_fields = fields


class AgreementAcceptanceSerializer(StringIDModelSerializer):
    class Meta:
        model = AgreementAcceptance
        fields = ["id", "problem", "agreement", "accepted_at"]
        read_only_fields = fields


class ProblemWorkSerializer(StringIDModelSerializer):
    user = UserTinySerializer(read_only=True)

    class Meta:
        model = ProblemWork
        fields = ["id", "status", "note", "created_at", "user"]
        read_only_fields = ["id", "created_at", "user"]


class WorkArtifactSerializer(StringIDModelSerializer):
    user = UserTinySerializer(read_only=True)

    class Meta:
        model = WorkArtifact
        fields = ["id", "title", "description", "url", "created_at", "user"]
        read_only_fields = ["id", "created_at", "user"]


class ProblemCommentSerializer(StringIDModelSerializer):
    user = UserTinySerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()

    class Meta:
        model = ProblemComment
        fields = ["id", "body", "created_at", "user", "likes_count", "has_liked"]
        read_only_fields = ["id", "created_at", "user", "likes_count", "has_liked"]

    def get_likes_count(self, obj: ProblemComment) -> int:
        value = getattr(obj, "likes_count", None)
        return int(value or 0)

    def get_has_liked(self, obj: ProblemComment) -> bool:
        return bool(getattr(obj, "has_liked", False))


class ArtifactCommentSerializer(StringIDModelSerializer):
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


class ProblemEventSerializer(StringIDModelSerializer):
    actor = UserTinySerializer(read_only=True, allow_null=True)

    class Meta:
        model = ProblemEvent
        fields = ["id", "type", "created_at", "actor", "metadata"]
        read_only_fields = fields
