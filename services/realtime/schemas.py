from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class PresenceEvent(BaseModel):
    type: Literal["presence"] = "presence"
    user_id: int
    thread_id: Optional[int]
    status: Literal["online", "offline", "typing"]
    timestamp: datetime | None = None


class MessageEvent(BaseModel):
    type: Literal["message"] = "message"
    thread_id: int
    message_id: int
    sender_id: int
    body: str
    created_at: datetime | None = None


class AckEvent(BaseModel):
    type: Literal["ack"] = "ack"
    message: str


RealtimeEvent = PresenceEvent | MessageEvent | AckEvent
