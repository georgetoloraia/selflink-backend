"""Deprecated Channels-based realtime consumer.

Use the FastAPI realtime service in services/realtime instead.
Enable only for legacy clients via REALTIME_CHANNELS_ENABLED=true.
"""

from __future__ import annotations

import urllib.parse

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class RealtimeConsumer(AsyncJsonWebsocketConsumer):
    close_codes = {
        "unauthorized": 4401,
        "forbidden": 4403,
    }

    async def connect(self) -> None:
        token = self._get_query_param("token")
        if not token:
            await self.close(code=self.close_codes["unauthorized"])
            return

        try:
            user = await self._authenticate_token(token)
        except (InvalidToken, TokenError):
            await self.close(code=self.close_codes["unauthorized"])
            return
        except Exception:
            await self.close(code=self.close_codes["forbidden"])
            return

        if not user or isinstance(user, AnonymousUser) or not user.is_active:
            await self.close(code=self.close_codes["forbidden"])
            return

        self.scope["user"] = user
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs) -> None:
        # MVP: ignore client payloads for now.
        return None

    async def user_event(self, event) -> None:
        payload = event.get("payload", {})
        await self.send_json(payload)

    def _get_query_param(self, key: str) -> str | None:
        raw = self.scope.get("query_string", b"").decode()
        params = urllib.parse.parse_qs(raw)
        values = params.get(key)
        return values[0] if values else None

    @database_sync_to_async
    def _authenticate_token(self, token: str):
        auth = JWTAuthentication()
        validated = auth.get_validated_token(token)
        return auth.get_user(validated)
