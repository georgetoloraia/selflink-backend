from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.messaging.models import Message
from apps.users.models import Block, Mute
from .services import NotificationPayload, dispatch_notification
from .tasks import notify_new_message as notify_new_message_task

User = get_user_model()


def notify_thread_message(message: Message) -> None:
    thread = message.thread
    sender_id = message.sender_id
    members = list(
        thread.members.exclude(user_id=sender_id)
        .select_related("user", "user__settings")
        .prefetch_related("user__devices")
    )
    if not members:
        return

    recipient_ids = [member.user_id for member in members if member.user_id]
    blocked_pairs = set(
        Block.objects.filter(
            Q(user_id=sender_id, target_id__in=recipient_ids)
            | Q(user_id__in=recipient_ids, target_id=sender_id)
        ).values_list("user_id", "target_id")
    )
    muted_recipient_ids = set(
        Mute.objects.filter(user_id__in=recipient_ids, target_id=sender_id).values_list(
            "user_id", flat=True
        )
    )

    recipients: list[User] = []
    push_targets: list[User] = []
    for member in members:
        user = member.user  # type: ignore[attr-defined]
        if not user:
            continue
        if (sender_id, user.id) in blocked_pairs or (user.id, sender_id) in blocked_pairs:
            continue
        recipients.append(user)
        if user.id not in muted_recipient_ids:
            push_targets.append(user)

    payload = NotificationPayload(
        type="message:new",
        payload={
            "thread_id": thread.id,
            "sender_id": sender_id,
        },
    )
    if recipients:
        dispatch_notification(recipients, payload, send_push=False)
    for user in push_targets:
        notify_new_message_task.delay(user.id, thread.id, message.id)
