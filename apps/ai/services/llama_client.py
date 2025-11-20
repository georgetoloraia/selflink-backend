from __future__ import annotations

import logging
from typing import Optional

from libs.llm import get_llm_client

logger = logging.getLogger(__name__)


class AIMentorError(Exception):
    """Raised when LLaMA/LLM calls fail."""


def generate_llama_response(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    client = get_llm_client()
    try:
        text = client.complete(system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature)
    except Exception as exc:
        logger.exception("LLM call failed")
        raise AIMentorError("AI mentor is unavailable at the moment.") from exc
    if max_tokens and len(text.split()) > max_tokens:
        text = " ".join(text.split()[:max_tokens])
    return text.strip()
