from __future__ import annotations

from datetime import datetime
from typing import Iterable

from apps.core.pubsub import publish_events
from .models import Message, Thread


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


def publish_typing_event(thread: Thread, user_id: int, is_typing: bool) -> None:
    payload = {
        "type": "typing",
        "thread_id": thread.id,
        "user_id": user_id,
        "is_typing": is_typing,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    user_ids: Iterable[int] = thread.members.values_list("user_id", flat=True)
    channels = [f"user:{uid}" for uid in set(user_ids) if uid != user_id]  # don't echo to sender
    if channels:
        publish_events(channels, payload)


def publish_member_left_event(thread_id: int, user_id: int, member_ids: Iterable[int]) -> None:
    payload = {
        "type": "member_left",
        "thread_id": thread_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    channels = [f"user:{uid}" for uid in set(member_ids)]
    if channels:
        publish_events(channels, payload)
