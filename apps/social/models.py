from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import BaseModel


class PostVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    FOLLOWERS = "followers", "Followers"
    PRIVATE = "private", "Private"


class PaidReactionTargetType(models.TextChoices):
    POST = "post", "Post"
    COMMENT = "comment", "Comment"


class Post(BaseModel):
    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="posts")
    text = models.TextField()
    visibility = models.CharField(max_length=16, choices=PostVisibility.choices, default=PostVisibility.PUBLIC)
    language = models.CharField(max_length=8, default="en")
    media = models.ManyToManyField("media.MediaAsset", blank=True, related_name="posts")
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __setattr__(self, name, value) -> None:
        if name == "video":
            post_video_cls = globals().get("PostVideo")
            if value is None or (post_video_cls and isinstance(value, post_video_cls)):
                self.__dict__.pop("_video_stub", None)
                return super().__setattr__(name, value)
            self.__dict__["_video_stub"] = value
            return
        super().__setattr__(name, value)


class PostImage(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="posts/images/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"PostImage<{self.id}>"


class PostVideo(BaseModel):
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="video")
    file = models.FileField(upload_to="posts/videos/")
    thumbnail = models.ImageField(upload_to="posts/videos/thumbnails/", null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=64, default="video/mp4")

    def __str__(self) -> str:  # pragma: no cover
        return f"PostVideo<{self.id}>"


class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="comments")
    text = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True
    )
    like_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]


class CommentImage(BaseModel):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="posts/images/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"CommentImage<{self.id}>"


class Like(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="likes")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.BigIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ("user", "content_type", "object_id")


class Follow(BaseModel):
    follower = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="following")
    followee = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="followers")

    class Meta:
        unique_together = ("follower", "followee")


class Gift(BaseModel):
    sender = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="sent_gifts")
    receiver = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="received_gifts")
    gift_type = models.ForeignKey("payments.GiftType", on_delete=models.PROTECT)
    payload = models.JSONField(default=dict, blank=True)


class Timeline(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="timeline_entries")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="timeline_entries")
    score = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("user", "post")
        ordering = ["-score", "-created_at"]


class PostLike(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        unique_together = ("user", "post")


class CommentLike(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="comment_likes")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        unique_together = ("user", "comment")


class PaidReaction(BaseModel):
    sender = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="paid_reactions_sent")
    target_type = models.CharField(max_length=16, choices=PaidReactionTargetType.choices)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="paid_reactions")
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="paid_reactions",
    )
    gift_type = models.ForeignKey("payments.GiftType", on_delete=models.PROTECT, related_name="paid_reactions")
    quantity = models.PositiveIntegerField(default=1)
    total_amount_cents = models.PositiveIntegerField()
    coin_event = models.ForeignKey("coin.CoinEvent", on_delete=models.PROTECT, related_name="paid_reactions")
    idempotency_key = models.UUIDField(unique=True, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["target_type", "created_at"]),
        ]
