from __future__ import annotations

import logging
from typing import Optional

from requests.exceptions import ReadTimeout

from libs.llm import get_llm_client

logger = logging.getLogger(__name__)

TIMEOUT_FALLBACK = (
    "The mentor response is taking too long. Please try again in a moment, "
    "or revisit this match with a fresh question."
)
ERROR_FALLBACK = "The mentor is unavailable right now. Please try again shortly."


class AIMentorError(Exception):
    """Raised when LLaMA/LLM calls fail."""


def generate_llama_response(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
) -> str:
    try:
        client = get_llm_client()
        text = client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    except ReadTimeout:
        logger.error("LLM call timed out", exc_info=True)
        return TIMEOUT_FALLBACK
    except Exception:
        logger.error("LLM call failed", exc_info=True)
        return ERROR_FALLBACK
    if max_tokens and len(text.split()) > max_tokens:
        text = " ".join(text.split()[:max_tokens])
    return text.strip()
