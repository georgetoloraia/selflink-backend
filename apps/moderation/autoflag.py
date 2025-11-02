from __future__ import annotations

import os
from typing import Iterable

from django.conf import settings

from apps.moderation.models import Report


def _banned_words() -> Iterable[str]:
    words = getattr(settings, "MODERATION_BANNED_WORDS", [])
    if isinstance(words, str):
        words = [w.strip() for w in words.split(",") if w.strip()]
    return [w.lower() for w in words]


def _contains_banned_word(text: str) -> bool:
    lowered = text.lower()
    for word in _banned_words():
        if word and word in lowered:
            return True
    return False


def auto_report_message(message) -> None:
    if not _banned_words() or not message.body:
        return
    if _contains_banned_word(message.body):
        Report.objects.get_or_create(
            reporter=message.sender,
            target_type=Report.TargetType.MESSAGE,
            target_id=message.id,
            defaults={
                "reason": "auto_flag:banned_word",
                "status": Report.Status.IN_REVIEW,
                "notes": message.body[:200],
            },
        )


def auto_report_post(post) -> None:
    if not _banned_words() or not post.text:
        return
    if _contains_banned_word(post.text):
        Report.objects.get_or_create(
            reporter=post.author,
            target_type=Report.TargetType.POST,
            target_id=post.id,
            defaults={
                "reason": "auto_flag:banned_word",
                "status": Report.Status.IN_REVIEW,
                "notes": post.text[:200],
            },
        )
