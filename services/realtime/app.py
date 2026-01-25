from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError

from .auth import AuthError, decode_token
from .config import settings
from .manager import manager
from .redis_client import get_async_redis, publish
from .schemas import AckEvent, MessageEvent, PresenceEvent

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


def get_user_id(websocket: WebSocket) -> int:
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("Realtime auth failed: missing token from %s", getattr(websocket.client, "host", "unknown"))
        raise AuthError("Missing token")
    payload = decode_token(token)
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise AuthError("Invalid token payload")
    websocket.state.token_sub = payload.get("sub") or payload.get("user_id")
    return int(user_id)


def _parse_channels(raw: str | None) -> list[str]:
    if not raw:
        return []
    channels = []
    for value in raw.split(","):
        value = value.strip()
        if not value:
            continue
        if value.startswith("post:") or value.startswith("comment:"):
            channels.append(value)
    return channels[:20]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int = Depends(get_user_id)) -> None:
    token_sub = getattr(websocket.state, "token_sub", None)
    logger.info("Realtime websocket connected user_id=%s token_sub=%s", user_id, token_sub)
    await manager.connect(user_id, websocket)
    ack = AckEvent(message="connected")
    logger.debug("realtime: sending event", extra={"type": ack.type, "target": "personal"})
    await manager.send_personal_message(user_id, ack.model_dump_json())

    redis = get_async_redis()
    pubsub = redis.pubsub()
    channels = [f"user:{user_id}", "broadcast"]
    channels.extend(_parse_channels(websocket.query_params.get("channels")))
    await pubsub.subscribe(*channels)
    pubsub_task = asyncio.create_task(_forward_pubsub(pubsub, websocket))
    await _publish_presence(user_id, "online")
    try:
        while True:
            raw = await websocket.receive_text()
            event = json.loads(raw)
            event_type = event.get("type")
            if event_type == "presence":
                payload = PresenceEvent(**event)
                response = payload.model_copy(update={"timestamp": datetime.utcnow()})
                logger.debug("realtime: sending event", extra={"type": response.type, "target": "broadcast"})
                await manager.broadcast(response.model_dump_json())
                with suppress(RedisError):
                    await publish("broadcast", response.model_dump())
            elif event_type == "message":
                payload = MessageEvent(**event)
                response = payload.model_copy(update={"created_at": datetime.utcnow()})
                logger.debug("realtime: sending event", extra={"type": response.type, "target": "broadcast"})
                await manager.broadcast(response.model_dump_json())
                with suppress(RedisError):
                    await publish(f"user:{payload.sender_id}", response.model_dump())
            else:
                await websocket.send_text(AckEvent(message="ignored").model_dump_json())
    except AuthError as exc:
        logger.warning("WebSocket auth error for user_id=%s: %s", user_id, exc)
        manager.disconnect(user_id, websocket)
        await websocket.close()
        await _publish_presence(user_id, "offline")
        return
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        await _publish_presence(user_id, "offline")
    except json.JSONDecodeError:
        await websocket.send_text(AckEvent(message="invalid-json").model_dump_json())
    finally:
        manager.disconnect(user_id, websocket)
        pubsub_task.cancel()
        with suppress(asyncio.CancelledError):
            await pubsub_task
        with suppress(Exception):
            await pubsub.unsubscribe(*channels)
            await pubsub.close()


async def _forward_pubsub(pubsub, websocket: WebSocket) -> None:
    try:
        async for message in pubsub.listen():  # type: ignore[attr-defined]
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            await websocket.send_text(data)
    except asyncio.CancelledError:
        raise
    except RedisError:
        await websocket.send_text(AckEvent(message="realtime-error").model_dump_json())


async def _publish_presence(user_id: int, status: str) -> None:
    event = PresenceEvent(
        user_id=user_id,
        thread_id=None,
        status=status,
        timestamp=datetime.utcnow(),
    )
    logger.debug("realtime: sending event", extra={"type": event.type, "target": "broadcast"})
    await manager.broadcast(event.model_dump_json())
    try:
        await publish("broadcast", event.model_dump())
    except RedisError:
        pass
