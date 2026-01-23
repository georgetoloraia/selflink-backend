from __future__ import annotations

from typing import List

from django.http import QueryDict
from django.db import models, transaction
from django.utils import timezone
from rest_framework import serializers

from apps.media.serializers import MediaAssetSerializer
from apps.media.models import MediaAsset
from apps.users.serializers import UserSerializer

from .models import (
    Comment,
    CommentImage,
    CommentLike,
    Follow,
    Gift,
    PaidReaction,
    Like,
    Post,
    PostImage,
    PostLike,
    PostVideo,
    Timeline,
)


class PostImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PostImage
        fields = ["id", "url", "order"]
        read_only_fields = ["id", "url", "order"]

    def get_url(self, obj: PostImage) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class PostVideoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    duration = serializers.FloatField(source="duration_seconds", read_only=True)

    class Meta:
        model = PostVideo
        fields = [
            "id",
            "url",
            "thumbnail_url",
            "duration",
            "width",
            "height",
            "mime_type",
        ]
        read_only_fields = fields

    def get_url(self, obj: PostVideo) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_thumbnail_url(self, obj: PostVideo) -> str | None:
        if not obj.thumbnail:
            return None
        request = self.context.get("request")
        url = obj.thumbnail.url
        if request:
            return request.build_absolute_uri(url)
        return url


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    media = MediaAssetSerializer(read_only=True, many=True)
    images = PostImageSerializer(read_only=True, many=True)
    video = PostVideoSerializer(read_only=True)
    image_urls = serializers.SerializerMethodField()
    media_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, write_only=True
    )
    images_upload = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    video_upload = serializers.FileField(
        write_only=True,
        required=False,
        allow_null=True,
    )
    liked = serializers.SerializerMethodField()
    viewer_has_liked = serializers.SerializerMethodField()
    recent_gifts = serializers.SerializerMethodField()

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
            "images",
            "image_urls",
            "images_upload",
            "video",
            "video_upload",
            "like_count",
            "comment_count",
            "liked",
            "viewer_has_liked",
            "recent_gifts",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "media",
            "images",
            "image_urls",
            "video",
            "like_count",
            "comment_count",
            "liked",
            "viewer_has_liked",
            "recent_gifts",
            "created_at",
        ]

    def get_liked(self, obj: Post) -> bool:
        return self.get_viewer_has_liked(obj)

    def get_viewer_has_liked(self, obj: Post) -> bool:
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return PostLike.objects.filter(user=request.user, post=obj).exists()

    def get_recent_gifts(self, obj: Post) -> list[dict]:
        recent = list(obj.paid_reactions.all()[:5]) if hasattr(obj, "paid_reactions") else []
        return PaidReactionSerializer(recent, many=True, context=self.context).data

    def create(self, validated_data: dict) -> Post:
        media_ids: List[int] = validated_data.pop("media_ids", [])
        images_upload = validated_data.pop("images_upload", [])
        video_upload = validated_data.pop("video_upload", None)
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
            for order, image in enumerate(images_upload):
                PostImage.objects.create(post=post, image=image, order=order)
            if video_upload:
                PostVideo.objects.create(
                    post=post,
                    file=video_upload,
                    duration_seconds=None,
                    width=None,
                    height=None,
                    mime_type=getattr(video_upload, "content_type", None) or "",
                )
        return post

    def to_internal_value(self, data):
        if isinstance(data, QueryDict):
            mutable = QueryDict(mutable=True)
            for key, values in data.lists():
                mutable.setlist(key, values)
            if "images_upload" not in mutable and "images" in mutable:
                mutable.setlist("images_upload", mutable.getlist("images"))
                del mutable["images"]
            if "video_upload" not in mutable and "video" in mutable:
                mutable["video_upload"] = mutable["video"]
            data = mutable
        elif isinstance(data, dict) and "images" in data and "images_upload" not in data:
            copied = data.copy()
            copied["images_upload"] = copied.pop("images")
            if "video" in copied and "video_upload" not in copied:
                copied["video_upload"] = copied.pop("video")
            data = copied
        return super().to_internal_value(data)

    def get_image_urls(self, obj: Post) -> list[str]:
        urls: list[str] = []
        request = self.context.get("request")
        for image in obj.images.all():
            if not image.image:
                continue
            url = image.image.url
            if request:
                url = request.build_absolute_uri(url)
            urls.append(url)
        return urls

    def validate(self, attrs: dict) -> dict:
        images = attrs.get("images_upload") or []
        video = attrs.get("video_upload")
        if images and video:
            raise serializers.ValidationError(
                {"video": "Choose either a video or images for a post in this version."}
            )
        if len(images) > 4:
            raise serializers.ValidationError({"images": "You can upload up to 4 images."})
        attrs["images_upload"] = images
        if video:
            allowed_mime = {"video/mp4", "video/quicktime"}
            mime = getattr(video, "content_type", None)
            if mime and mime not in allowed_mime:
                raise serializers.ValidationError({"video": "Unsupported video format."})
            max_size = 50 * 1024 * 1024  # 50 MB guardrail for v1 uploads
            if hasattr(video, "size") and video.size and video.size > max_size:
                raise serializers.ValidationError({"video": "Video file is too large."})
        attrs["video_upload"] = video
        return attrs


class CommentImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = CommentImage
        fields = ["id", "url", "order"]
        read_only_fields = ["id", "url", "order"]

    def get_url(self, obj: CommentImage) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    images = CommentImageSerializer(read_only=True, many=True)
    image_urls = serializers.SerializerMethodField()
    images_upload = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    like_count = serializers.IntegerField(read_only=True)
    viewer_has_liked = serializers.SerializerMethodField()
    recent_gifts = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "author",
            "text",
            "parent",
            "images",
            "image_urls",
            "images_upload",
            "like_count",
            "viewer_has_liked",
            "recent_gifts",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "images",
            "image_urls",
            "like_count",
            "viewer_has_liked",
            "recent_gifts",
            "created_at",
        ]

    def to_internal_value(self, data):
        if isinstance(data, QueryDict):
            mutable = data.copy()
            if "images_upload" not in mutable and "images" in mutable:
                mutable.setlist("images_upload", mutable.getlist("images"))
                del mutable["images"]
            data = mutable
        elif isinstance(data, dict) and "images" in data and "images_upload" not in data:
            copied = data.copy()
            copied["images_upload"] = copied.pop("images")
            data = copied
        return super().to_internal_value(data)

    def get_image_urls(self, obj: Comment) -> list[str]:
        urls: list[str] = []
        request = self.context.get("request")
        for image in obj.images.all():
            if not image.image:
                continue
            url = image.image.url
            if request:
                url = request.build_absolute_uri(url)
            urls.append(url)
        return urls

    def get_viewer_has_liked(self, obj: Comment) -> bool:
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return CommentLike.objects.filter(user=request.user, comment=obj).exists()

    def get_recent_gifts(self, obj: Comment) -> list[dict]:
        recent = list(obj.paid_reactions.all()[:5]) if hasattr(obj, "paid_reactions") else []
        return PaidReactionSerializer(recent, many=True, context=self.context).data

    def create(self, validated_data: dict) -> Comment:
        images = validated_data.pop("images_upload", [])
        request = self.context.get("request")
        user = request.user if request else None
        if user is None or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        if validated_data.get("parent") and validated_data["parent"].post_id != validated_data["post"].id:
            raise serializers.ValidationError("Parent comment must belong to the same post")
        with transaction.atomic():
            comment = Comment.objects.create(author=user, **validated_data)
            for order, image in enumerate(images):
                CommentImage.objects.create(comment=comment, image=image, order=order)
            Post.objects.filter(pk=comment.post_id).update(
                comment_count=models.F("comment_count") + 1
            )
        return comment

    def validate(self, attrs: dict) -> dict:
        images = attrs.get("images_upload") or []
        text = (attrs.get("text") or "").strip()
        if not text and not images:
            raise serializers.ValidationError("Write a comment or attach a photo.")
        if len(images) > 4:
            raise serializers.ValidationError({"images": "You can upload up to 4 images."})
        attrs["text"] = text
        attrs["images_upload"] = images
        return attrs


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


class PaidReactionSerializer(serializers.ModelSerializer):
    gift_type = serializers.SerializerMethodField()
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)

    class Meta:
        model = PaidReaction
        fields = [
            "id",
            "sender_id",
            "target_type",
            "post",
            "comment",
            "gift_type",
            "quantity",
            "total_amount_cents",
            "created_at",
            "idempotency_key",
        ]

    def get_gift_type(self, obj: PaidReaction) -> dict:
        from apps.payments.serializers import GiftTypeSerializer

        return GiftTypeSerializer(obj.gift_type, context=self.context).data


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
