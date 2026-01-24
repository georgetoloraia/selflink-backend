from __future__ import annotations

import logging

from django.db import models
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics, permissions, viewsets

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from django.core.exceptions import ValidationError

from apps.coin.services.ledger import create_spend, get_balance_cents, get_or_create_user_account
from apps.payments.models import GiftType
from apps.feed.cache import FeedCache
from apps.feed.composer import compose_home_feed_items, extract_cursor_from_url
from .models import Comment, CommentLike, Gift, PaidReaction, Post, PostLike, Timeline
from apps.moderation.autoflag import auto_report_post
from .serializers import (
    CommentSerializer,
    FeedRequestSerializer,
    GiftSerializer,
    PaidReactionSerializer,
    PostSerializer,
    TimelineSerializer,
)

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return request.META.get("HTTP_X_REQUEST_ID", "")


@method_decorator(ratelimit(key="user", rate="30/min", method="POST", block=True), name="create")
class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    throttle_scope = None
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
        like, created = PostLike.objects.get_or_create(user=request.user, post=post)
        if created:
            Post.objects.filter(pk=post.pk).update(like_count=models.F("like_count") + 1)
            FeedCache.invalidate_first_page(request.user.id)
            FeedCache.invalidate_first_page(post.author_id)
        like_count = Post.objects.filter(pk=post.pk).values_list("like_count", flat=True).first() or 0
        return Response({"liked": True, "like_count": like_count})

    @action(methods=["post", "delete"], detail=True, permission_classes=[permissions.IsAuthenticated])
    def unlike(self, request: Request, pk: str | None = None) -> Response:
        post = self.get_object()
        deleted, _ = PostLike.objects.filter(user=request.user, post=post).delete()
        if deleted:
            Post.objects.filter(pk=post.pk, like_count__gt=0).update(
                like_count=models.F("like_count") - 1
            )
            FeedCache.invalidate_first_page(request.user.id)
            FeedCache.invalidate_first_page(post.author_id)
        like_count = Post.objects.filter(pk=post.pk).values_list("like_count", flat=True).first() or 0
        return Response({"liked": False, "like_count": like_count})

    @action(
        methods=["post"],
        detail=True,
        permission_classes=[permissions.IsAuthenticated],
        url_path="gifts",
        throttle_scope="paid_reaction",
    )
    def gifts(self, request: Request, pk: str | None = None) -> Response:
        post = self.get_object()
        gift_type_id = request.data.get("gift_type_id")
        quantity = int(request.data.get("quantity") or 1)
        note = str(request.data.get("note") or "")
        idempotency_key = request.META.get("HTTP_IDEMPOTENCY_KEY")

        if quantity < 1 or quantity > 50:
            return Response(
                {"detail": "Quantity must be between 1 and 50.", "code": "invalid_quantity"},
                status=400,
            )
        try:
            gift_type = GiftType.objects.get(id=gift_type_id)
        except GiftType.DoesNotExist:
            return Response({"detail": "GiftType not found.", "code": "invalid_gift_type"}, status=404)
        if not gift_type.is_active:
            return Response({"detail": "GiftType inactive.", "code": "gift_inactive"}, status=400)

        price_cents = gift_type.price_slc_cents or gift_type.price_cents
        total_amount_cents = price_cents * quantity
        if total_amount_cents <= 0:
            return Response({"detail": "invalid_amount", "code": "invalid_amount"}, status=400)

        existing = None
        if idempotency_key:
            existing = PaidReaction.objects.filter(idempotency_key=idempotency_key).select_related(
                "gift_type", "coin_event"
            ).first()
            if existing:
                if (
                    existing.sender_id != request.user.id
                    or existing.post_id != post.id
                    or existing.gift_type_id != gift_type.id
                    or existing.quantity != quantity
                ):
                    return Response(
                        {"detail": "Idempotency key conflict.", "code": "idempotency_conflict"},
                        status=400,
                    )
                account = get_or_create_user_account(request.user)
                balance_cents = get_balance_cents(account.account_key)
                return Response(
                    {
                        "reaction": PaidReactionSerializer(existing, context={"request": request}).data,
                        "slc_balance_cents": balance_cents,
                        "currency": "SLC",
                    }
                )

        reference = f"gift:post:{post.id}:{gift_type.key or gift_type.id}"
        note_text = note or f"gift:{gift_type.key or gift_type.id} x{quantity}"
        try:
            coin_event = create_spend(
                user=request.user,
                amount_cents=total_amount_cents,
                reference=reference,
                note=note_text,
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            code_map = {
                "insufficient_funds": "insufficient_funds",
                "Amount must be positive.": "invalid_amount",
                "Coin account is not active.": "account_inactive",
                "User coin accounts cannot be system accounts.": "account_invalid",
            }
            code = code_map.get(detail, "coin_error")
            return Response({"detail": detail, "code": code}, status=400)

        reaction = PaidReaction.objects.create(
            sender=request.user,
            target_type=PaidReaction.TargetType.POST,
            post=post,
            gift_type=gift_type,
            quantity=quantity,
            total_amount_cents=total_amount_cents,
            coin_event=coin_event,
            idempotency_key=idempotency_key or None,
        )
        account = get_or_create_user_account(request.user)
        balance_cents = get_balance_cents(account.account_key)
        logger.info(
            "gift_spend.created request_id=%s user_id=%s target=post target_id=%s gift_type_id=%s "
            "quantity=%s amount_cents=%s reference=%s coin_event_id=%s",
            _request_id(request),
            request.user.id,
            post.id,
            gift_type.id,
            quantity,
            total_amount_cents,
            reference,
            coin_event.id,
        )
        return Response(
            {
                "reaction": PaidReactionSerializer(reaction, context={"request": request}).data,
                "slc_balance_cents": balance_cents,
                "currency": "SLC",
            },
            status=201,
        )


@method_decorator(ratelimit(key="user", rate="60/min", method="POST", block=True), name="create")
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    throttle_scope = None
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

    @action(methods=["post"], detail=True, permission_classes=[permissions.IsAuthenticated])
    def like(self, request: Request, pk: str | None = None) -> Response:
        comment = self.get_object()
        like, created = CommentLike.objects.get_or_create(user=request.user, comment=comment)
        if created:
            Comment.objects.filter(pk=comment.pk).update(like_count=models.F("like_count") + 1)
        like_count = Comment.objects.filter(pk=comment.pk).values_list("like_count", flat=True).first() or 0
        return Response({"liked": True, "like_count": like_count})

    @action(methods=["post", "delete"], detail=True, permission_classes=[permissions.IsAuthenticated])
    def unlike(self, request: Request, pk: str | None = None) -> Response:
        comment = self.get_object()
        deleted, _ = CommentLike.objects.filter(user=request.user, comment=comment).delete()
        if deleted:
            Comment.objects.filter(pk=comment.pk, like_count__gt=0).update(like_count=models.F("like_count") - 1)
        like_count = Comment.objects.filter(pk=comment.pk).values_list("like_count", flat=True).first() or 0
        return Response({"liked": False, "like_count": like_count})

    @action(
        methods=["post"],
        detail=True,
        permission_classes=[permissions.IsAuthenticated],
        url_path="gifts",
        throttle_scope="paid_reaction",
    )
    def gifts(self, request: Request, pk: str | None = None) -> Response:
        comment = self.get_object()
        gift_type_id = request.data.get("gift_type_id")
        quantity = int(request.data.get("quantity") or 1)
        note = str(request.data.get("note") or "")
        idempotency_key = request.META.get("HTTP_IDEMPOTENCY_KEY")

        if quantity < 1 or quantity > 50:
            return Response(
                {"detail": "Quantity must be between 1 and 50.", "code": "invalid_quantity"},
                status=400,
            )
        try:
            gift_type = GiftType.objects.get(id=gift_type_id)
        except GiftType.DoesNotExist:
            return Response({"detail": "GiftType not found.", "code": "invalid_gift_type"}, status=404)
        if not gift_type.is_active:
            return Response({"detail": "GiftType inactive.", "code": "gift_inactive"}, status=400)

        price_cents = gift_type.price_slc_cents or gift_type.price_cents
        total_amount_cents = price_cents * quantity
        if total_amount_cents <= 0:
            return Response({"detail": "invalid_amount", "code": "invalid_amount"}, status=400)

        existing = None
        if idempotency_key:
            existing = PaidReaction.objects.filter(idempotency_key=idempotency_key).select_related(
                "gift_type", "coin_event"
            ).first()
            if existing:
                if (
                    existing.sender_id != request.user.id
                    or existing.comment_id != comment.id
                    or existing.gift_type_id != gift_type.id
                    or existing.quantity != quantity
                ):
                    return Response(
                        {"detail": "Idempotency key conflict.", "code": "idempotency_conflict"},
                        status=400,
                    )
                account = get_or_create_user_account(request.user)
                balance_cents = get_balance_cents(account.account_key)
                return Response(
                    {
                        "reaction": PaidReactionSerializer(existing, context={"request": request}).data,
                        "slc_balance_cents": balance_cents,
                        "currency": "SLC",
                    }
                )

        reference = f"gift:comment:{comment.id}:{gift_type.key or gift_type.id}"
        note_text = note or f"gift:{gift_type.key or gift_type.id} x{quantity}"
        try:
            coin_event = create_spend(
                user=request.user,
                amount_cents=total_amount_cents,
                reference=reference,
                note=note_text,
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            code_map = {
                "insufficient_funds": "insufficient_funds",
                "Amount must be positive.": "invalid_amount",
                "Coin account is not active.": "account_inactive",
                "User coin accounts cannot be system accounts.": "account_invalid",
            }
            code = code_map.get(detail, "coin_error")
            return Response({"detail": detail, "code": code}, status=400)

        reaction = PaidReaction.objects.create(
            sender=request.user,
            target_type=PaidReaction.TargetType.COMMENT,
            comment=comment,
            gift_type=gift_type,
            quantity=quantity,
            total_amount_cents=total_amount_cents,
            coin_event=coin_event,
            idempotency_key=idempotency_key or None,
        )
        account = get_or_create_user_account(request.user)
        balance_cents = get_balance_cents(account.account_key)
        logger.info(
            "gift_spend.created request_id=%s user_id=%s target=comment target_id=%s gift_type_id=%s "
            "quantity=%s amount_cents=%s reference=%s coin_event_id=%s",
            _request_id(request),
            request.user.id,
            comment.id,
            gift_type.id,
            quantity,
            total_amount_cents,
            reference,
            coin_event.id,
        )
        return Response(
            {
                "reaction": PaidReactionSerializer(reaction, context={"request": request}).data,
                "slc_balance_cents": balance_cents,
                "currency": "SLC",
            },
            status=201,
        )


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
