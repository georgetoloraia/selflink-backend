from __future__ import annotations

from typing import Iterable

from django.contrib.auth import get_user_model

from apps.messaging.models import Thread
from .services import NotificationPayload, dispatch_notification

User = get_user_model()


def notify_thread_message(thread: Thread, sender_id: int) -> None:
    recipients: Iterable[User] = thread.members.exclude(user_id=sender_id).values_list("user", flat=False)
    users = [member.user for member in thread.members.exclude(user_id=sender_id).select_related("user")]  # type: ignore[attr-defined]
    payload = NotificationPayload(
        type="message:new",
        payload={
            "thread_id": thread.id,
            "sender_id": sender_id,
        },
    )
    if users:
        dispatch_notification(users, payload)
