from __future__ import annotations

import asyncio
from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: Dict[int, Set[WebSocket]] = {}
        self._locks: Dict[int, asyncio.Lock] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(user_id, set()).add(websocket)
        self._locks.setdefault(id(websocket), asyncio.Lock())

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        websockets = self.connections.get(user_id)
        if not websockets:
            return
        websockets.discard(websocket)
        if not websockets:
            self.connections.pop(user_id, None)
        self._locks.pop(id(websocket), None)

    def _is_connected(self, websocket: WebSocket) -> bool:
        return (
            websocket.application_state == WebSocketState.CONNECTED
            and websocket.client_state == WebSocketState.CONNECTED
        )

    async def safe_send_text(self, websocket: WebSocket, message: str) -> bool:
        if not self._is_connected(websocket):
            return False
        lock = self._locks.setdefault(id(websocket), asyncio.Lock())
        async with lock:
            if not self._is_connected(websocket):
                return False
            try:
                await websocket.send_text(message)
                return True
            except (WebSocketDisconnect, RuntimeError):
                return False
            except Exception:
                return False

    async def send_personal_message(self, user_id: int, message: str) -> None:
        stale: Set[WebSocket] = set()
        for ws in list(self.connections.get(user_id, set())):
            ok = await self.safe_send_text(ws, message)
            if not ok:
                stale.add(ws)
        for ws in stale:
            self.disconnect(user_id, ws)

    async def broadcast(self, message: str) -> None:
        stale_map: Dict[int, Set[WebSocket]] = {}
        for user_id, sockets in list(self.connections.items()):
            for ws in list(sockets):
                ok = await self.safe_send_text(ws, message)
                if not ok:
                    stale_map.setdefault(user_id, set()).add(ws)
        for user_id, sockets in stale_map.items():
            for ws in sockets:
                self.disconnect(user_id, ws)


manager = ConnectionManager()
