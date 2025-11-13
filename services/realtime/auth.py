from __future__ import annotations

from typing import Any, Dict

import jwt

from .config import settings
import logging


logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when realtime auth fails."""


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        logger.warning("Realtime auth failed: expired token")
        raise AuthError("Expired token") from exc
    except jwt.InvalidSignatureError as exc:
        logger.warning("Realtime auth failed: invalid signature")
        raise AuthError("Invalid signature") from exc
    except jwt.DecodeError as exc:
        logger.warning("Realtime auth failed: malformed token")
        raise AuthError("Malformed token") from exc
    except jwt.PyJWTError as exc:  # pragma: no cover - thin wrapper
        logger.warning("Realtime auth failed: %s", exc)
        raise AuthError("Invalid token") from exc
    return payload
