from __future__ import annotations

from typing import Any, Dict

import jwt

from .config import settings


class AuthError(Exception):
    """Raised when realtime auth fails."""


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:  # pragma: no cover - thin wrapper
        raise AuthError("Invalid token") from exc
    return payload
