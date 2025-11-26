from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics, permissions, status, viewsets

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.feed.cache import FeedCache
from apps.feed.composer import compose_home_feed_items, extract_cursor_from_url
from .models import Comment, Follow, Gift, Like, Post, Timeline
from apps.moderation.autoflag import auto_report_post
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
        .select_related("video")
        .prefetch_related("media", "images")
        .all()
    )

    def perform_create(self, serializer: PostSerializer) -> None:  # type: ignore[override]
        post = serializer.save()
        auto_report_post(post)
        FeedCache.invalidate_first_page(post.author_id)

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
            FeedCache.invalidate_first_page(request.user.id)
            FeedCache.invalidate_first_page(post.author_id)
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
            FeedCache.invalidate_first_page(request.user.id)
            FeedCache.invalidate_first_page(post.author_id)
        return Response({"liked": False})


@method_decorator(ratelimit(key="user", rate="60/min", method="POST", block=True), name="create")
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = (
        Comment.objects.select_related("author", "post", "parent")
        .prefetch_related("images")
        .all()
    )

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset()
        post_id = self.request.query_params.get("post")
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset

    def perform_create(self, serializer: CommentSerializer) -> None:  # type: ignore[override]
        comment = serializer.save()
        FeedCache.invalidate_first_page(comment.author_id)
        FeedCache.invalidate_first_page(comment.post.author_id)


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
            .select_related("post", "post__author", "post__author__settings", "post__video")
            .prefetch_related("post__media", "post__images")
        )
        since = params.validated_data.get("since")
        if since:
            queryset = queryset.filter(created_at__gte=since)
        return queryset

    def list(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        entries = page if page is not None else queryset
        items = compose_home_feed_items(
            entries,
            serializer_context=self.get_serializer_context(),
            user=request.user,
        )

        next_cursor = None
        if page is not None and getattr(self, "paginator", None):
            next_cursor = extract_cursor_from_url(
                self.paginator.get_next_link(),
                cursor_param=self.paginator.cursor_query_param,
            )

        return Response({"items": items, "next": next_cursor})
