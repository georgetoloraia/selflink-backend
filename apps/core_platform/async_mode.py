from __future__ import annotations

import os
from typing import Any, Optional


_TRUE_VALUES = {"1", "true", "yes"}
_FALSE_VALUES = {"0", "false", "no"}


def _normalize_flag(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def _parse_async_override(request) -> Optional[bool]:
    param = (getattr(request, "query_params", {}) or {}).get("async")
    param_value = _normalize_flag(param)
    if param_value in _TRUE_VALUES:
        return True
    if param_value in _FALSE_VALUES:
        return False

    header = (getattr(request, "headers", {}) or {}).get("X-Async")
    header_value = _normalize_flag(header)
    if header_value in _TRUE_VALUES:
        return True
    if header_value in _FALSE_VALUES:
        return False
    return None


def is_sync_requested(request) -> bool:
    header = (getattr(request, "headers", {}) or {}).get("X-Sync")
    header_value = _normalize_flag(header)
    return header_value in _TRUE_VALUES


def should_run_async(request) -> bool:
    """
    Determine whether to return async task responses for heavy endpoints.

    Priority order:
    - explicit header X-Sync: true (forces sync)
    - explicit query param ?async=true/false
    - explicit header X-Async: true/false
    - environment default INTELLIGENCE_ASYNC_DEFAULT=true
    """
    if is_sync_requested(request):
        return False

    override = _parse_async_override(request)
    if override is not None:
        return override

    return os.getenv("INTELLIGENCE_ASYNC_DEFAULT", "false").lower() == "true"


def should_run_async_default(request, default_async: bool = False) -> bool:
    """
    Decide async behavior with an endpoint-specific default, while still honoring overrides.
    """
    if is_sync_requested(request):
        return False

    override = _parse_async_override(request)
    if override is not None:
        return override

    if default_async:
        return True

    return os.getenv("INTELLIGENCE_ASYNC_DEFAULT", "false").lower() == "true"
