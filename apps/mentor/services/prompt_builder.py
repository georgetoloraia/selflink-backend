from __future__ import annotations

from . import personality


def build_messages(user, user_message: str, mode: str, language: str | None) -> list[dict]:
    """
    Build a minimal messages list for the LLM.
    For V1 we use a simple base persona followed by the user message.
    """
    base_system_prompt = personality.get_base_persona_prompt(language=language)
    messages = [
        {"role": "system", "content": base_system_prompt},
        {"role": "user", "content": user_message},
    ]
    return messages
