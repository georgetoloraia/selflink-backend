from __future__ import annotations

from typing import Iterable

from apps.core.pubsub import publish_events
from .models import Message


def publish_message_event(message: Message) -> None:
    payload = {
        "type": "message",
        "thread_id": message.thread_id,
        "message_id": message.id,
        "sender_id": message.sender_id,
        "body": message.body,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }
    user_ids: Iterable[int] = message.thread.members.values_list("user_id", flat=True)
    channels = [f"user:{user_id}" for user_id in set(user_ids)]
    if channels:
        publish_events(channels, payload)
