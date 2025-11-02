from __future__ import annotations

from typing import List

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone
from rest_framework import serializers

from apps.media.serializers import MediaAssetSerializer
from apps.media.models import MediaAsset
from apps.users.serializers import UserSerializer

from .models import Comment, Follow, Gift, Like, Post, Timeline


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    media = MediaAssetSerializer(read_only=True, many=True)
    media_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, write_only=True
    )
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "text",
            "visibility",
            "language",
            "media",
            "media_ids",
            "like_count",
            "comment_count",
            "liked",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "media",
            "like_count",
            "comment_count",
            "liked",
            "created_at",
        ]

    def get_liked(self, obj: Post) -> bool:
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return Like.objects.filter(
            user=request.user,
            content_type=ContentType.objects.get_for_model(Post),
            object_id=obj.id,
        ).exists()

    def create(self, validated_data: dict) -> Post:
        media_ids: List[int] = validated_data.pop("media_ids", [])
        request = self.context.get("request")
        user = request.user if request else None
        if user is None or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        with transaction.atomic():
            post = Post.objects.create(author=user, **validated_data)
            if media_ids:
                assets = list(
                    MediaAsset.objects.filter(id__in=media_ids, owner=user)
                )
                post.media.set(assets)
        return post


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "text", "parent", "created_at"]
        read_only_fields = ["id", "author", "created_at"]

    def create(self, validated_data: dict) -> Comment:
        request = self.context.get("request")
        user = request.user if request else None
        if user is None or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        if validated_data.get("parent") and validated_data["parent"].post_id != validated_data["post"].id:
            raise serializers.ValidationError("Parent comment must belong to the same post")
        with transaction.atomic():
            comment = Comment.objects.create(author=user, **validated_data)
            Post.objects.filter(pk=comment.post_id).update(
                comment_count=models.F("comment_count") + 1
            )
        return comment


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ["id", "follower", "followee", "created_at"]
        read_only_fields = ["id", "follower", "created_at"]

    def create(self, validated_data: dict) -> Follow:
        request = self.context.get("request")
        follower = request.user if request else None
        if follower is None or follower.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        if follower.id == validated_data["followee"].id:
            raise serializers.ValidationError("Cannot follow yourself")
        follow, _ = Follow.objects.get_or_create(follower=follower, followee=validated_data["followee"])
        return follow


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ["id", "content_type", "object_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class GiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gift
        fields = ["id", "sender", "receiver", "gift_type", "payload", "created_at"]
        read_only_fields = ["id", "sender", "created_at"]

    def create(self, validated_data: dict) -> Gift:
        request = self.context.get("request")
        sender = request.user if request else None
        if sender is None or sender.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        gift = Gift.objects.create(sender=sender, **validated_data)
        return gift


class TimelineSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)

    class Meta:
        model = Timeline
        fields = ["id", "post", "score", "created_at"]


class FeedRequestSerializer(serializers.Serializer):
    cursor = serializers.CharField(required=False)
    since = serializers.DateTimeField(required=False)

    def validate_since(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Cannot query future timestamps")
        return value
