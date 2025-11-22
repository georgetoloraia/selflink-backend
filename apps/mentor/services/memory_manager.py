from __future__ import annotations


def store_conversation(user, session, user_msg: str, mentor_msg: str) -> None:
    """
    Placeholder hook for future memory and vector DB integration.
    """
    return None


def retrieve_relevant_memories(user, user_message: str, mode: str) -> list[str]:
    """
    Return relevant memory snippets for the user.
    V1 returns an empty list.
    """
    return []
