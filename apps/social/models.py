from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import BaseModel


class Post(BaseModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS = "followers", "Followers"
        PRIVATE = "private", "Private"

    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="posts")
    text = models.TextField()
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC)
    language = models.CharField(max_length=8, default="en")
    media = models.ManyToManyField("media.MediaAsset", blank=True, related_name="posts")
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]


class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="comments")
    text = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True
    )

    class Meta:
        ordering = ["created_at"]


class CommentImage(BaseModel):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="comment_images/")
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
