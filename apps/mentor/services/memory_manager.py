from __future__ import annotations

from typing import Dict, List

from apps.mentor.models import MentorMessage, MentorSession

# Limit how many past turns we feed back into the LLM to keep prompts small.
DEFAULT_HISTORY_LIMIT = 20
DAILY_HISTORY_LIMIT = 6


def store_conversation(user, session, user_msg: str, mentor_msg: str) -> None:
    """
    Placeholder hook for future memory and vector DB integration.
    """
    return None


def load_conversation_history(
    user,
    limit: int | None = None,
    mode: str | None = None,
    session: MentorSession | None = None,
) -> List[Dict[str, str]]:
    """
    Return recent chat history for the user in LLM-friendly format.
    Only user/assistant messages are returned (no system prompts).
    """
    effective_limit = (
        limit
        if limit is not None
        else (DAILY_HISTORY_LIMIT if mode == MentorSession.MODE_DAILY else DEFAULT_HISTORY_LIMIT)
    )

    qs = MentorMessage.objects.filter(session__user=user)
    if session:
        qs = qs.filter(session=session)
    elif mode:
        qs = qs.filter(session__mode=mode)

    qs = qs.order_by("-created_at").values("role", "content")[:effective_limit]

    messages: List[Dict[str, str]] = []
    for msg in reversed(list(qs)):
        role_value = msg["role"]
        role = (
            "assistant"
            if role_value in (MentorMessage.Role.MENTOR, MentorMessage.Role.ASSISTANT)
            else "user"
        )
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
