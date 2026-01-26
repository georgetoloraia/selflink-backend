from __future__ import annotations

import asyncio

from starlette.websockets import WebSocketState

from services.realtime.manager import ConnectionManager


class FakeWebSocket:
    def __init__(self, *, fail: bool = False, state: WebSocketState = WebSocketState.CONNECTED) -> None:
        self.fail = fail
        self.application_state = state
        self.client_state = state
        self.sent: list[str] = []

    async def send_text(self, message: str) -> None:
        if self.fail:
            raise RuntimeError("Cannot call send")
        self.sent.append(message)


def test_broadcast_removes_dead_socket() -> None:
    manager = ConnectionManager()
    good = FakeWebSocket()
    dead = FakeWebSocket(fail=True)
    manager.connections = {1: {good, dead}}

    asyncio.run(manager.broadcast("hello"))

    assert good in manager.connections[1]
    assert dead not in manager.connections[1]


def test_safe_send_rejects_disconnected() -> None:
    manager = ConnectionManager()
    ws = FakeWebSocket(state=WebSocketState.DISCONNECTED)

    result = asyncio.run(manager.safe_send_text(ws, "hello"))

    assert result is False
    assert ws.sent == []
