from __future__ import annotations

from datetime import datetime
from typing import Iterable

from apps.core.pubsub import publish_events
from .models import Message, Thread
from apps.users.models import User


def _serialize_message(message: Message) -> dict:
    from .serializers import MessageSerializer

    serializer = MessageSerializer(message)
    data = dict(serializer.data)
    message_id = data.get("id")
    thread_id = data.get("thread")
    if message_id is not None:
        data["id"] = str(message_id)
    if thread_id is not None:
        data["thread"] = str(thread_id)
    return data


def publish_message_event(message: Message) -> None:
    payload = {
        "type": "message:new",
        "payload": _serialize_message(message),
    }
    user_ids: Iterable[int] = message.thread.members.values_list("user_id", flat=True)
    channels = [f"user:{user_id}" for user_id in set(user_ids)]
    if channels:
        publish_events(channels, payload)


def publish_message_status_event(message: Message) -> None:
    payload = {
        "type": "message:status",
        "payload": {
            "id": str(message.id),
            "thread": str(message.thread_id),
            "status": message.status,
            "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
            "read_at": message.read_at.isoformat() if message.read_at else None,
            "client_uuid": message.client_uuid,
        },
    }
    user_ids: Iterable[int] = message.thread.members.values_list("user_id", flat=True)
    channels = [f"user:{user_id}" for user_id in set(user_ids)]
    if channels:
        publish_events(channels, payload)


def publish_typing_event(thread: Thread, user: User, is_typing: bool) -> None:
    payload = {
        "type": "typing",
        "thread_id": thread.id,
        "user_id": user.id,
        "user_name": getattr(user, "name", "") or None,
        "user_handle": getattr(user, "handle", "") or None,
        "is_typing": is_typing,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    user_ids: Iterable[int] = thread.members.values_list("user_id", flat=True)
    channels = [f"user:{uid}" for uid in set(user_ids) if uid != user.id]  # don't echo to sender
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
