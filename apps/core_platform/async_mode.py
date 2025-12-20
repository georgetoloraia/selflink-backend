from __future__ import annotations

import os


def should_run_async(request) -> bool:
    """
    Determine whether to return async task responses for heavy endpoints.

    Priority order:
    - explicit query param ?async=true
    - explicit header X-Async: true
    - environment default INTELLIGENCE_ASYNC_DEFAULT=true
    """
    param = (getattr(request, "query_params", {}) or {}).get("async")
    if isinstance(param, str) and param.lower() in {"1", "true", "yes"}:
        return True

    header = (getattr(request, "headers", {}) or {}).get("X-Async")
    if isinstance(header, str) and header.lower() in {"1", "true", "yes"}:
        return True

    return os.getenv("INTELLIGENCE_ASYNC_DEFAULT", "false").lower() == "true"

