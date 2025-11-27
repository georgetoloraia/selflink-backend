from __future__ import annotations

from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from .events import (
    publish_member_left_event,
    publish_message_event,
    publish_message_reaction_event,
    publish_message_status_event,
    publish_typing_event,
)
from apps.notifications.consumers import notify_thread_message
from .models import Message, MessageAttachment, MessageReaction, Thread, ThreadMember
from .serializers import MessageSerializer, ThreadSerializer, aggregate_reactions
from .typing import get_typing_users, start_typing, stop_typing
from apps.moderation.autoflag import auto_report_message
from apps.users.models import Block, User
from apps.users.serializers import UserSerializer


def _normalize_message_payload(request: Request, thread: Thread | None = None) -> dict:
    raw_data = request.data
    if isinstance(raw_data, QueryDict):
        data = raw_data.dict()
    else:
        data = dict(raw_data)
    for file_key in getattr(request, "FILES", {}):
        data.pop(file_key, None)
    if thread:
        data["thread"] = str(thread.id)
    text_value = data.pop("text", None)
    if text_value and not data.get("body"):
        data["body"] = text_value
    return data


def _validate_attachment_files(files) -> list[dict]:
    if not files:
        return []

    specs: list[dict] = []
    for uploaded in files:
        mime = getattr(uploaded, "content_type", "") or ""
        if mime.startswith("image/"):
            attachment_type = MessageAttachment.AttachmentType.IMAGE
        elif mime.startswith("video/"):
            attachment_type = MessageAttachment.AttachmentType.VIDEO
        else:
            raise ValidationError("Unsupported attachment type.")
        specs.append({"file": uploaded, "type": attachment_type, "mime_type": mime})

    type_set = {spec["type"] for spec in specs}
    if len(type_set) > 1:
        raise ValidationError("Cannot mix images and videos in the same message.")
    only_type = next(iter(type_set))
    if only_type == MessageAttachment.AttachmentType.IMAGE and len(specs) > 4:
        raise ValidationError("You can attach up to 4 images per message.")
    if only_type == MessageAttachment.AttachmentType.VIDEO and len(specs) > 1:
        raise ValidationError("Only one video can be attached per message.")
    return specs


def _is_blocked_between(user_id: int, other_user_id: int) -> bool:
    return Block.objects.filter(
        Q(user_id=user_id, target_id=other_user_id) | Q(user_id=other_user_id, target_id=user_id)
    ).exists()


def _create_message_with_attachments(request: Request, thread: Thread | None = None) -> tuple[Message, bool]:
    data = _normalize_message_payload(request, thread=thread)
    serializer = MessageSerializer(data=data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    thread_obj = serializer.validated_data.get("thread")
    if thread_obj and not thread_obj.members.filter(user=request.user).exists():
        raise PermissionDenied("Not a member of this thread")
    if thread_obj and not thread_obj.is_group:
        other_ids = list(
            thread_obj.members.exclude(user=request.user).values_list("user_id", flat=True)
        )
        if any(_is_blocked_between(request.user.id, other_id) for other_id in other_ids):
            raise PermissionDenied("Cannot send messages to this user.")

    attachment_files = request.FILES.getlist("attachments")
    attachment_specs = _validate_attachment_files(attachment_files)

    with transaction.atomic():
        message = serializer.save()
        deduped = getattr(serializer, "_deduped", False)
        if not deduped and attachment_specs:
            attachments = [
                MessageAttachment(
                    message=message,
                    file=spec["file"],
                    type=spec["type"],
                    mime_type=spec["mime_type"],
                )
                for spec in attachment_specs
            ]
            MessageAttachment.objects.bulk_create(attachments)

    message = (
        Message.objects.select_related("sender", "thread", "reply_to", "reply_to__sender")
        .prefetch_related("attachments", "reply_to__attachments")
        .get(pk=message.id)
    )
    return message, deduped


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
        payload = request.data or {}
        last_read_message_id = payload.get("last_read_message_id") or payload.get("last_read_id")
        if isinstance(last_read_message_id, str) and not last_read_message_id.strip():
            last_read_message_id = None
        target_message = None
        if last_read_message_id:
            try:
                target_message = thread.messages.get(pk=int(last_read_message_id))
            except (ValueError, TypeError, Message.DoesNotExist):
                return Response({"detail": "Invalid last_read_message_id"}, status=status.HTTP_400_BAD_REQUEST)
        if target_message is None:
            target_message = thread.messages.order_by("-id").first()
        if not target_message:
            return Response(status=status.HTTP_204_NO_CONTENT)

        membership = ThreadMember.objects.filter(thread=thread, user=request.user).first()
        current_last_read_id = membership.last_read_message_id if membership else None
        if current_last_read_id and current_last_read_id >= target_message.id:
            last_read_id = current_last_read_id
        else:
            last_read_id = target_message.id
            ThreadMember.objects.filter(thread=thread, user=request.user).update(
                last_read_message=target_message
            )

        now = timezone.now()
        unread_messages = list(
            thread.messages.filter(id__lte=last_read_id)
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

        return Response({"status": "read", "last_read_message_id": str(last_read_id)})

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
        if _is_blocked_between(request.user.id, target.id):
            return Response({"detail": "Messaging is blocked between these users."}, status=status.HTTP_403_FORBIDDEN)

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

    @action(detail=True, methods=["post"], url_path="messages")
    def create_message(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        try:
            message, deduped = _create_message_with_attachments(request, thread=thread)
        except ValidationError as exc:
            return Response({"detail": exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MessageSerializer(message, context={"request": request})
        status_code = status.HTTP_200_OK if deduped else status.HTTP_201_CREATED
        if not deduped:
            publish_message_event(message)
            notify_thread_message(message)
            auto_report_message(message)
        return Response(serializer.data, status=status_code)

    @action(detail=True, methods=["get"], url_path="sync")
    def sync(self, request: Request, pk: str | None = None) -> Response:
        thread = self.get_object()
        since = request.query_params.get("since")
        queryset = (
            thread.messages.select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("attachments", "reply_to__attachments")
            .order_by("created_at")
        )
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
        return (
            queryset.select_related("sender", "thread", "reply_to", "reply_to__sender")
            .prefetch_related("attachments", "reply_to__attachments")
        )

    def create(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        try:
            message, deduped = _create_message_with_attachments(request)
        except ValidationError as exc:
            return Response({"detail": exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(message)
        if not deduped:
            publish_message_event(message)
            notify_thread_message(message)
            auto_report_message(message)

        status_code = status.HTTP_200_OK if deduped else status.HTTP_201_CREATED
        return Response(serializer.data, status=status_code, headers=self.get_success_headers(serializer.data))

    @action(detail=True, methods=["get", "post"], url_path="reactions")
    def reactions(self, request: Request, pk: str | None = None) -> Response:
        message = self.get_object()
        if request.method.lower() == "get":
            data = aggregate_reactions(message, current_user_id=request.user.id)
            return Response({"reactions": data})

        emoji = request.data.get("emoji")
        if not emoji or not isinstance(emoji, str):
            return Response({"detail": "emoji is required"}, status=status.HTTP_400_BAD_REQUEST)
        if len(emoji) > 16:
            return Response({"detail": "emoji is too long"}, status=status.HTTP_400_BAD_REQUEST)

        existing = MessageReaction.objects.filter(message=message, user=request.user, emoji=emoji)
        action_value = "removed" if existing.exists() else "added"
        if action_value == "removed":
            existing.delete()
        else:
            MessageReaction.objects.create(message=message, user=request.user, emoji=emoji)

        reactions = aggregate_reactions(message, current_user_id=request.user.id)
        publish_message_reaction_event(message, emoji, request.user.id, action_value)
        return Response({"action": action_value, "reactions": reactions}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="ack")
    def ack(self, request: Request, pk: str | None = None) -> Response:
        message = self.get_object()
        status_value = request.data.get("status")
        if status_value != Message.Status.DELIVERED:
            return Response({"detail": "status must be 'delivered'."}, status=status.HTTP_400_BAD_REQUEST)

        if not message.thread.members.filter(user=request.user).exists():
            raise PermissionDenied("Not a member of this thread")

        if message.status == Message.Status.SENT:
            now = timezone.now()
            message.status = Message.Status.DELIVERED
            if not message.delivered_at:
                message.delivered_at = now
            message.save(update_fields=["status", "delivered_at", "updated_at"])
            publish_message_status_event(message)

        serializer = MessageSerializer(message, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
