from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

PLACEHOLDER_REPLY = (
    "This is a placeholder answer from SelfLink AI Mentor. LLM server is not configured yet."
)


def chat(messages: List[Dict[str, Any]]) -> str:
    """
    Send chat messages to the configured LLM server.
    Falls back to a placeholder when the server is not configured or errors occur.
    """
    base_url = os.getenv("MENTOR_LLM_BASE_URL")
    model = os.getenv("MENTOR_LLM_MODEL", "selflink-mentor")

    if not base_url:
        return PLACEHOLDER_REPLY

    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            json={"model": model, "messages": messages},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if content:
            return content
    except Exception as exc:  # pragma: no cover - fallback path
        logger.warning("Mentor LLM chat failed: %s", exc, exc_info=True)

    return PLACEHOLDER_REPLY
