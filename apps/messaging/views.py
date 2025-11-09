from __future__ import annotations

from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from .events import publish_member_left_event, publish_message_event, publish_typing_event
from apps.notifications.consumers import notify_thread_message
from .models import Message, Thread, ThreadMember
from .serializers import MessageSerializer, ThreadSerializer
from .typing import get_typing_users, start_typing, stop_typing
from apps.moderation.autoflag import auto_report_message
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

    def perform_create(self, serializer: ThreadSerializer) -> None:  # type: ignore[override]
        serializer.save()

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        last_message = thread.messages.order_by("-created_at").first()
        if not last_message:
            return Response(status=status.HTTP_204_NO_CONTENT)
        ThreadMember.objects.filter(thread=thread, user=request.user).update(
            last_read_message=last_message
        )
        return Response({"status": "read"})

    @action(detail=True, methods=["get", "post"], url_path="typing")
    def typing(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        if not thread.members.filter(user=request.user).exists():
            raise PermissionDenied("Not a member of this thread")
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

    def perform_create(self, serializer: MessageSerializer) -> None:  # type: ignore[override]
        thread = serializer.validated_data.get("thread")
        if thread and not thread.members.filter(user=self.request.user).exists():
            raise PermissionDenied("Not a member of this thread")
        message = serializer.save()
        publish_message_event(message)
        notify_thread_message(message.thread, message.sender_id)
        auto_report_message(message)
