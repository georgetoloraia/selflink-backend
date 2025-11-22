from __future__ import annotations


def preprocess_user_message(text: str) -> dict:
    """
    Analyze incoming user message for safety concerns.
    V1 returns an empty dict to keep the pipeline non-blocking.
    """
    return {}


def postprocess_mentor_reply(text: str) -> tuple[str, dict]:
    """
    Post-process mentor reply for safety.
    V1 returns the text unchanged and an empty flags dict.
    """
    return text, {}
