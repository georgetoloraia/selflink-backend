from __future__ import annotations

from django.db import transaction
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from .events import (
    publish_member_left_event,
    publish_message_event,
    publish_message_status_event,
    publish_typing_event,
)
from apps.notifications.consumers import notify_thread_message
from .models import Message, Thread, ThreadMember
from .serializers import MessageSerializer, ThreadSerializer
from .typing import get_typing_users, start_typing, stop_typing
from apps.moderation.autoflag import auto_report_message
from apps.users.models import User
from apps.users.serializers import UserSerializer


@method_decorator(ratelimit(key="user", rate="20/min", method="POST", block=True), name="create")
class ThreadViewSet(viewsets.ModelViewSet):
    serializer_class = ThreadSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["created_at", "updated_at"]
    ordering = "-updated_at"
    search_fields = ["title", "members__user__handle", "members__user__name"]

    def get_queryset(self):  # type: ignore[override]
        last_message_subquery = Message.objects.filter(thread=OuterRef("pk")).order_by("-created_at")
        return (
            Thread.objects.filter(members__user=self.request.user)
            .annotate(
                last_message_body=Subquery(last_message_subquery.values("body")[:1]),
                last_message_created_at=Subquery(last_message_subquery.values("created_at")[:1]),
            )
            .select_related("created_by")
            .prefetch_related("members__user", "members__last_read_message")
            .distinct()
        )

    def get_object(self):  # type: ignore[override]
        lookup_value = self.kwargs.get(self.lookup_field or "pk")
        queryset = Thread.objects.select_related("created_by").prefetch_related(
            "members__user", "members__last_read_message"
        )
        thread = get_object_or_404(queryset, pk=lookup_value)
        if not thread.members.filter(user=self.request.user).exists():
            raise PermissionDenied("Not a member of this thread")
        return thread

    def perform_create(self, serializer: ThreadSerializer) -> None:  # type: ignore[override]
        serializer.save()

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        last_message = thread.messages.order_by("-created_at").first()
        if not last_message:
            return Response(status=status.HTTP_204_NO_CONTENT)
        now = timezone.now()
        unread_messages = list(
            thread.messages.filter(created_at__lte=last_message.created_at)
            .exclude(sender=request.user)
            .exclude(status=Message.Status.READ)
        )
        for msg in unread_messages:
            msg.status = Message.Status.READ
            msg.read_at = now
            if not msg.delivered_at:
                msg.delivered_at = now
            msg.save(update_fields=["status", "delivered_at", "read_at", "updated_at"])
            publish_message_status_event(msg)
        ThreadMember.objects.filter(thread=thread, user=request.user).update(
            last_read_message=last_message
        )
        return Response({"status": "read"})

    @action(detail=True, methods=["get", "post"], url_path="typing")
    def typing(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        if request.method.lower() == "get":
            user_ids = get_typing_users(thread.id)
            member_map = {
                member.user_id: member
                for member in thread.members.select_related("user").filter(user_id__in=user_ids)
            }
            users = [
                UserSerializer(member_map[user_id].user, context={"request": request}).data
                for user_id in user_ids
                if user_id in member_map
            ]
            return Response({"typing_user_ids": user_ids, "users": users})

        is_typing = bool(request.data.get("is_typing", True))
        if is_typing:
            start_typing(request.user.id, thread.id)
        else:
            stop_typing(request.user.id, thread.id)
        publish_typing_event(thread, request.user, is_typing)
        return Response({"is_typing": is_typing})

    @action(detail=True, methods=["post"], url_path="leave")
    def leave(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        membership_qs = ThreadMember.objects.filter(thread=thread, user=request.user)
        if not membership_qs.exists():
            raise PermissionDenied("Not a member of this thread")

        with transaction.atomic():
            membership_qs.delete()
            remaining_member_ids = list(
                ThreadMember.objects.filter(thread=thread).values_list("user_id", flat=True)
            )
            if not remaining_member_ids:
                thread.delete()
            else:
                transaction.on_commit(
                    lambda: publish_member_left_event(thread.id, request.user.id, remaining_member_ids)
                )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="direct")
    def direct(self, request: Request) -> Response:
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Target user not found"}, status=status.HTTP_404_NOT_FOUND)
        if target == request.user:
            return Response({"detail": "Cannot start a direct thread with yourself"}, status=status.HTTP_400_BAD_REQUEST)

        thread = (
            Thread.objects.filter(is_group=False, members__user=request.user)
            .filter(members__user=target)
            .distinct()
            .annotate(member_total=Count("members", distinct=True))
            .filter(member_total=2)
            .select_related("created_by")
            .prefetch_related("members__user", "members__last_read_message")
            .first()
        )
        if thread:
            serializer = self.get_serializer(thread)
            return Response(serializer.data, status=status.HTTP_200_OK)

        payload = {"participant_ids": [target.id]}
        initial_message = request.data.get("initial_message")
        if isinstance(initial_message, str) and initial_message.strip():
            payload["initial_message"] = initial_message.strip()
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        thread = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="sync")
    def sync(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        since = request.query_params.get("since")
        queryset = thread.messages.select_related("sender").order_by("created_at")
        if since:
            try:
                since_id = int(since)
                queryset = queryset.filter(id__gt=since_id)
            except (TypeError, ValueError):
                parsed = parse_datetime(since)
                if parsed:
                    if timezone.is_naive(parsed):
                        parsed = timezone.make_aware(parsed, timezone=timezone.utc)
                    queryset = queryset.filter(created_at__gt=parsed)
        serializer = MessageSerializer(queryset, many=True, context={"request": request})
        return Response({"messages": serializer.data})


@method_decorator(ratelimit(key="user", rate="60/min", method="POST", block=True), name="create")
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        thread_id = self.request.query_params.get("thread")
        queryset = Message.objects.filter(thread__members__user=self.request.user)
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return queryset.select_related("sender", "thread")

    def create(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        thread = serializer.validated_data.get("thread")
        if thread and not thread.members.filter(user=request.user).exists():
            raise PermissionDenied("Not a member of this thread")

        message = serializer.save()
        deduped = getattr(serializer, "_deduped", False)
        if not deduped:
            publish_message_event(message)
            notify_thread_message(message.thread, message.sender_id)
            auto_report_message(message)

        headers = self.get_success_headers(serializer.data)
        status_code = status.HTTP_200_OK if deduped else status.HTTP_201_CREATED
        return Response(serializer.data, status=status_code, headers=headers)

    @action(detail=True, methods=["post"], url_path="ack")
    def ack(self, request: Request, pk: str | None = None) -> Response:
        message = self.get_object()
        status_value = request.data.get("status")
        if status_value != Message.Status.DELIVERED:
            return Response({"detail": "status must be 'delivered'."}, status=status.HTTP_400_BAD_REQUEST)

        if message.status != Message.Status.READ:
            now = timezone.now()
            if message.status in (Message.Status.PENDING, Message.Status.SENT):
                message.status = Message.Status.DELIVERED
            if not message.delivered_at:
                message.delivered_at = now
            message.save(update_fields=["status", "delivered_at", "updated_at"])
            publish_message_status_event(message)

        serializer = MessageSerializer(message, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
