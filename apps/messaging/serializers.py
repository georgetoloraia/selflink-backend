from __future__ import annotations

from typing import List
from django.db.models import Count

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.db import IntegrityError

from apps.users.serializers import UserSerializer
from apps.users.models import User
from apps.notifications.consumers import notify_thread_message
from apps.moderation.autoflag import auto_report_message

from .events import publish_message_event
from .models import Message, MessageAttachment, Thread, ThreadMember


from apps.messaging.models import MessageStatus
class ThreadMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ThreadMember
        fields = ["id", "user", "role", "created_at", "updated_at"]
        read_only_fields = fields


class ThreadSerializer(serializers.ModelSerializer):
    members = ThreadMemberSerializer(many=True, read_only=True)
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), write_only=True
    )
    initial_message = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Thread
        fields = [
            "id",
            "is_group",
            "title",
            "members",
            "participants",
            "last_message",
            "unread_count",
            "participant_ids",
            "initial_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "members",
            "participants",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def validate_participant_ids(self, values: List[int]) -> List[int]:
        request = self.context.get("request")
        cleaned = list(dict.fromkeys(values))
        if not cleaned:
            raise serializers.ValidationError("At least one participant is required.")
        existing_ids = set(
            User.objects.filter(id__in=cleaned).values_list("id", flat=True)  # type: ignore[arg-type]
        )
        missing = [str(user_id) for user_id in cleaned if user_id not in existing_ids]
        if missing:
            raise serializers.ValidationError(
                f"Unknown participant IDs: {', '.join(missing)}"
            )
        if request and request.user.is_authenticated:
            if request.user.id not in cleaned:
                cleaned.append(request.user.id)
            if not any(member_id != request.user.id for member_id in cleaned):
                raise serializers.ValidationError("Add at least one participant besides yourself.")
        return cleaned

    def create(self, validated_data: dict) -> Thread:
        participant_ids = validated_data.pop("participant_ids", [])
        initial_message = validated_data.pop("initial_message", "").strip()
        request = self.context.get("request")
        user = request.user if request else None
        if not user or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")
        with transaction.atomic():
            thread = Thread.objects.create(created_by=user, **validated_data)
            member_ids = participant_ids or [user.id]
            ThreadMember.objects.bulk_create(
                [ThreadMember(thread=thread, user_id=member_id) for member_id in member_ids],
                ignore_conflicts=True,
            )
            if initial_message:
                message = Message.objects.create(thread=thread, sender=user, body=initial_message)
                thread.updated_at = timezone.now()
                thread.save(update_fields=["updated_at"])
                publish_message_event(message)
                notify_thread_message(message)
                auto_report_message(message)
        return thread

    def get_participants(self, obj: Thread) -> List[dict]:
        request = self.context.get("request")
        user_id = request.user.id if request and request.user.is_authenticated else None
        members = obj.members.all()
        return [
            UserSerializer(member.user, context=self.context).data
            for member in members
            if getattr(member, "user", None) and member.user_id != user_id
        ]

    def get_last_message(self, obj: Thread) -> dict | None:
        body = getattr(obj, "last_message_body", None)
        created_at = getattr(obj, "last_message_created_at", None)
        if body is not None or created_at is not None:
            if body is None and created_at is None:
                return None
            return {"body": body, "created_at": created_at}
        last_message = obj.messages.order_by("-created_at").values("body", "created_at").first()
        return last_message

    def get_unread_count(self, obj: Thread) -> int:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        membership = next(
            (member for member in obj.members.all() if member.user_id == request.user.id),
            None,
        )
        if not membership:
            return 0
        last_read = membership.last_read_message
        message_qs = obj.messages.all()
        # A message is unread for a user if its id is greater than that user's last_read_message_id.
        if not last_read:
            return message_qs.count()
        return message_qs.filter(id__gt=last_read.id).count()


def aggregate_reactions(message: Message, current_user_id: int | None = None) -> list[dict]:
    emoji_counts = list(message.reactions.values("emoji").annotate(count=Count("id")))
    reacted_emojis: set[str] = set()
    if current_user_id:
        reacted_emojis = set(
            message.reactions.filter(user_id=current_user_id).values_list("emoji", flat=True)
        )
    return [
        {
            "emoji": entry["emoji"],
            "count": entry["count"],
            "reacted_by_current_user": entry["emoji"] in reacted_emojis,
        }
        for entry in emoji_counts
    ]


def _preview_text(body: str | None, limit: int = 120) -> str:
    if not body:
        return ""
    text = body.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class MessageAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    duration = serializers.FloatField(source="duration_seconds", required=False)

    class Meta:
        model = MessageAttachment
        fields = ["id", "url", "type", "mime_type", "width", "height", "duration"]
        read_only_fields = fields

    def get_url(self, obj: MessageAttachment) -> str | None:
        try:
            return obj.file.url
        except Exception:
            return None


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    reactions = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    reply_to_message_id = serializers.PrimaryKeyRelatedField(
        source="reply_to",
        queryset=Message.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "thread",
            "sender",
            "reply_to",
            "reply_to_message_id",
            "body",
            "type",
            "meta",
            "status",
            "delivered_at",
            "read_at",
            "client_uuid",
            "created_at",
            "attachments",
            "reactions",
        ]
        read_only_fields = [
            "id",
            "sender",
            "created_at",
            "status",
            "delivered_at",
            "read_at",
            "reply_to",
            "reactions",
        ]

    def create(self, validated_data: dict) -> Message:
        request = self.context.get("request")
        user = request.user if request else None
        if not user or user.is_anonymous:
            raise serializers.ValidationError("Authentication required")

        client_uuid = validated_data.get("client_uuid")
        thread = validated_data.get("thread")

        self._deduped = False
        if client_uuid and thread:
            existing = Message.objects.filter(
                thread=thread, sender=user, client_uuid=client_uuid
            ).first()
            if existing:
                self._deduped = True
                return existing

        try:
            message = Message.objects.create(sender=user, status=MessageStatus.SENT, **validated_data)
        except IntegrityError:
            existing = Message.objects.filter(thread=thread, client_uuid=client_uuid).first()
            if existing:
                self._deduped = True
                return existing
            raise
        if message.thread_id:
            message.thread.save(update_fields=["updated_at"])
        return message

    def get_validators(self):  # type: ignore[override]
        validators = super().get_validators()
        return [validator for validator in validators if not isinstance(validator, UniqueTogetherValidator)]

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        reply_to: Message | None = attrs.get("reply_to")
        thread: Thread | None = attrs.get("thread") or getattr(self.instance, "thread", None)
        if reply_to and thread and reply_to.thread_id != thread.id:
            raise serializers.ValidationError({"reply_to_message_id": "Must reply within the same thread."})
        return attrs

    def get_reactions(self, obj: Message) -> list[dict]:
        request = self.context.get("request")
        user_id = request.user.id if request and request.user.is_authenticated else None
        return aggregate_reactions(obj, current_user_id=user_id)

    def get_reply_to(self, obj: Message) -> dict | None:
        target = getattr(obj, "reply_to", None)
        if not target:
            return None
        has_attachments = target.attachments.exists()
        return {
            "id": str(target.id),
            "sender_id": target.sender_id,
            "text_preview": _preview_text(target.body),
            "has_attachments": has_attachments,
        }
