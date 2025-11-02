from __future__ import annotations

import json
from datetime import datetime

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect

from .auth import AuthError, decode_token
from .config import settings
from .manager import manager
from .schemas import AckEvent, MessageEvent, PresenceEvent

app = FastAPI(title=settings.app_name)


def get_user_id(websocket: WebSocket) -> int:
    token = websocket.query_params.get("token")
    if not token:
        raise AuthError("Missing token")
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Invalid token payload")
    return int(user_id)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int = Depends(get_user_id)) -> None:
    await manager.connect(user_id, websocket)
    await manager.send_personal_message(
        user_id,
        AckEvent(message="connected").model_dump_json(),
    )
    try:
        while True:
            raw = await websocket.receive_text()
            event = json.loads(raw)
            event_type = event.get("type")
            if event_type == "presence":
                payload = PresenceEvent(**event)
                response = payload.model_copy(update={"timestamp": datetime.utcnow()})
                await manager.broadcast(response.model_dump_json())
            elif event_type == "message":
                payload = MessageEvent(**event)
                response = payload.model_copy(update={"created_at": datetime.utcnow()})
                await manager.broadcast(response.model_dump_json())
            else:
                await websocket.send_text(AckEvent(message="ignored").model_dump_json())
    except (WebSocketDisconnect, AuthError):
        manager.disconnect(user_id, websocket)
        await manager.broadcast(
            PresenceEvent(
                user_id=user_id,
                thread_id=None,
                status="offline",
                timestamp=datetime.utcnow(),
            ).model_dump_json()
        )
    except json.JSONDecodeError:
        await websocket.send_text(AckEvent(message="invalid-json").model_dump_json())
    finally:
        manager.disconnect(user_id, websocket)
