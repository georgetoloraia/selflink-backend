from __future__ import annotations

from typing import Dict, List

from apps.mentor.models import MentorMessage

# Limit how many past turns we feed back into the LLM to keep prompts small.
DEFAULT_HISTORY_LIMIT = 20


def store_conversation(user, session, user_msg: str, mentor_msg: str) -> None:
    """
    Placeholder hook for future memory and vector DB integration.
    """
    return None


def load_conversation_history(user, limit: int = DEFAULT_HISTORY_LIMIT) -> List[Dict[str, str]]:
    """
    Return recent chat history for the user in LLM-friendly format.
    Only user/assistant messages are returned (no system prompts).
    """
    qs = (
        MentorMessage.objects.filter(session__user=user)
        .order_by("-created_at")
        .values("role", "content")[:limit]
    )
    messages: List[Dict[str, str]] = []
    for msg in reversed(list(qs)):
        role = "assistant" if msg["role"] == MentorMessage.Role.MENTOR else "user"
        content = msg["content"] or ""
        if not content:
            continue
        messages.append({"role": role, "content": content})
    return messages


def retrieve_relevant_memories(user, user_message: str, mode: str) -> list[str]:
    """
    Return relevant memory snippets for the user.
    V1 returns an empty list.
    """
    return []
