from __future__ import annotations

from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        websockets = self.connections.get(user_id)
        if not websockets:
            return
        websockets.discard(websocket)
        if not websockets:
            self.connections.pop(user_id, None)

    async def send_personal_message(self, user_id: int, message: str) -> None:
        stale: Set[WebSocket] = set()
        for ws in self.connections.get(user_id, set()):
            try:
                await ws.send_text(message)
            except (WebSocketDisconnect, RuntimeError):
                stale.add(ws)
        for ws in stale:
            self.disconnect(user_id, ws)

    async def broadcast(self, message: str) -> None:
        stale_map: Dict[int, Set[WebSocket]] = {}
        for user_id, sockets in self.connections.items():
            for ws in list(sockets):
                try:
                    await ws.send_text(message)
                except (WebSocketDisconnect, RuntimeError):
                    stale_map.setdefault(user_id, set()).add(ws)
        for user_id, sockets in stale_map.items():
            for ws in sockets:
                self.disconnect(user_id, ws)


manager = ConnectionManager()
