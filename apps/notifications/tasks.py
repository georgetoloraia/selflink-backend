from __future__ import annotations

from celery import shared_task

from apps.messaging.models import Message
from .services import NotificationPayload, send_push_notification
from apps.users.models import User


def _truncate_text(text: str | None, limit: int = 140) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3] + "..."


@shared_task
def notify_new_message(user_id: int, thread_id: int, message_id: int) -> None:
    try:
        user = User.objects.select_related("settings").prefetch_related("devices").get(id=user_id)
    except User.DoesNotExist:
        return
    try:
        message = Message.objects.select_related("sender").get(id=message_id)
    except Message.DoesNotExist:
        return

    sender_name = getattr(message.sender, "name", "") or getattr(message.sender, "handle", "")
    payload = NotificationPayload(
        type="message:new",
        payload={
            "thread_id": thread_id,
            "message_id": message_id,
            "sender_id": message.sender_id,
            "sender_name": sender_name,
            "text": _truncate_text(message.body),
        },
    )
    send_push_notification([user], payload)
