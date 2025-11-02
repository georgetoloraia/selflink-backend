from __future__ import annotations

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from .events import publish_message_event
from apps.notifications.consumers import notify_thread_message
from .models import Message, Thread, ThreadMember
from .serializers import MessageSerializer, ThreadSerializer


class ThreadViewSet(viewsets.ModelViewSet):
    serializer_class = ThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        return (
            Thread.objects.filter(members__user=self.request.user)
            .select_related("created_by")
            .prefetch_related("members__user")
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
