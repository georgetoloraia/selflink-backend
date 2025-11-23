from __future__ import annotations

from typing import Any, Dict, List

from apps.mentor.services.context import build_user_astro_context
from apps.mentor.services import personality


def build_messages(user: Any, language: str | None, history: List[Dict[str, str]], user_text: str) -> List[Dict[str, str]]:
    """
    Build the full message list for the mentor LLM:
    - system persona prompt
    - system user astro/matrix context
    - chat history
    - new user message
    """
    system_prompt = personality.get_prompt(language)
    user_context = build_user_astro_context(user)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": user_context},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages
