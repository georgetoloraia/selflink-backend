from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Comment, Follow, Gift, Like, Post, Timeline
from .serializers import (
    CommentSerializer,
    FeedRequestSerializer,
    GiftSerializer,
    PostSerializer,
    TimelineSerializer,
)


@method_decorator(ratelimit(key="user", rate="30/min", method="POST", block=True), name="create")
class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = (
        Post.objects.select_related("author", "author__settings")
        .prefetch_related("media")
        .all()
    )

    def perform_create(self, serializer: PostSerializer) -> None:  # type: ignore[override]
        serializer.save()

    @action(methods=["post"], detail=True, permission_classes=[permissions.IsAuthenticated])
    def like(self, request: Request, pk: str | None = None) -> Response:
        post = self.get_object()
        content_type = ContentType.objects.get_for_model(Post)
        like, created = Like.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=post.id,
        )
        if created:
            Post.objects.filter(pk=post.pk).update(like_count=models.F("like_count") + 1)
        return Response({"liked": True})

    @action(methods=["post"], detail=True, permission_classes=[permissions.IsAuthenticated])
    def unlike(self, request: Request, pk: str | None = None) -> Response:
        post = self.get_object()
        content_type = ContentType.objects.get_for_model(Post)
        deleted, _ = Like.objects.filter(
            user=request.user,
            content_type=content_type,
            object_id=post.id,
        ).delete()
        if deleted:
            Post.objects.filter(pk=post.pk, like_count__gt=0).update(
                like_count=models.F("like_count") - 1
            )
        return Response({"liked": False})


@method_decorator(ratelimit(key="user", rate="60/min", method="POST", block=True), name="create")
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Comment.objects.select_related("author", "post", "parent").all()

    def perform_create(self, serializer: CommentSerializer) -> None:  # type: ignore[override]
        serializer.save()


class GiftViewSet(viewsets.ModelViewSet):
    serializer_class = GiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        return Gift.objects.filter(sender=self.request.user)

    def perform_create(self, serializer: GiftSerializer) -> None:  # type: ignore[override]
        serializer.save()


class FeedView(generics.ListAPIView):
    serializer_class = TimelineSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context.setdefault("request", self.request)
        return context

    def get_queryset(self):  # type: ignore[override]
        params = FeedRequestSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        queryset = (
            Timeline.objects.filter(user=self.request.user)
            .select_related("post", "post__author", "post__author__settings")
            .prefetch_related("post__media")
        )
        since = params.validated_data.get("since")
        if since:
            queryset = queryset.filter(created_at__gte=since)
        return queryset
