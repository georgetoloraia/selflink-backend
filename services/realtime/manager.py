from __future__ import annotations

from typing import Dict, Set

from fastapi import WebSocket


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
        for ws in self.connections.get(user_id, set()):
            await ws.send_text(message)

    async def broadcast(self, message: str) -> None:
        for sockets in self.connections.values():
            for ws in sockets:
                await ws.send_text(message)


manager = ConnectionManager()
