from __future__ import annotations

from typing import Tuple

from django.utils import timezone

from apps.users.models import User

POSITIVE_KEYWORDS = {"grateful", "happy", "excited", "energized"}
NEGATIVE_KEYWORDS = {"sad", "tired", "lonely", "anxious", "stressed"}


def analyze_sentiment(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in POSITIVE_KEYWORDS):
        return "positive"
    if any(word in lowered for word in NEGATIVE_KEYWORDS):
        return "negative"
    return "neutral"


def generate_mentor_reply(user: User, question: str) -> Tuple[str, str]:
    sentiment = analyze_sentiment(question)
    intro = {
        "positive": "I feel the light in what you shared.",
        "negative": "I hear the weight you're carrying.",
        "neutral": "Thank you for sharing your moment today.",
    }[sentiment]
    name = user.name or user.handle
    task = _suggest_micro_task(sentiment)
    answer = (
        f"{intro} {name}, let's take a mindful breath together. "
        f"One gentle step: {task}"
    )
    return answer, sentiment


def _suggest_micro_task(sentiment: str) -> str:
    today = timezone.localdate().strftime("%A")
    if sentiment == "positive":
        return "share one gratitude note with someone you care about."
    if sentiment == "negative":
        return "pause for 5 minutes, breathe slowly, and write down what you need right now."
    return f"write a short reflection about how {today} has unfolded for you so far."
