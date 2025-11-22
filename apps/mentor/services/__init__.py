from __future__ import annotations

import os
from typing import Tuple

from django.utils import timezone

from apps.users.models import User
from libs.llm import get_llm_client
from ..models import MentorMemory

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
    memory = _get_memory(user)
    if _llm_enabled():
        try:
            llm = get_llm_client()
            system_prompt = _system_prompt(user, memory)
            user_prompt = _user_prompt(question, sentiment, memory)
            answer = llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            _update_memory(memory, question, answer, sentiment)
            return answer, sentiment
        except Exception:  # pragma: no cover - fall back on failure
            pass
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
    _update_memory(memory, question, answer, sentiment)
    return answer, sentiment


def _suggest_micro_task(sentiment: str) -> str:
    today = timezone.localdate().strftime("%A")
    if sentiment == "positive":
        return "share one gratitude note with someone you care about."
    if sentiment == "negative":
        return "pause for 5 minutes, breathe slowly, and write down what you need right now."
    return f"write a short reflection about how {today} has unfolded for you so far."


def _system_prompt(user: User, memory: MentorMemory) -> str:
    traits = {
        "name": user.name or user.handle,
        "locale": user.locale,
        "bio": (user.bio or "")[:200],
    }
    memory_context = memory.last_summary or "No summary yet."
    return (
        "You are SelfLink Mentor, a compassionate guide who offers concise, warm reflections. "
        "Always acknowledge the user's emotional tone, offer one grounded insight, and end with a small, doable task. "
        f"User traits: name={traits['name']}, locale={traits['locale']}, bio={traits['bio']}. "
        f"Recent mentor memory: {memory_context}. "
        "Never provide medical or diagnostic advice. Keep responses under 120 words."
    )


def _user_prompt(question: str, sentiment: str, memory: MentorMemory) -> str:
    entries = memory.notes.get("entries", [])
    recent_reflection = "\n".join(
        f"- {entry.get('question', '')[:80]}" for entry in entries[-3:]
    )
    prompt = (
        "User message:\n"
        f"{question}\n\n"
        f"Detected sentiment: {sentiment}. Provide one empathetic response and a 1-step actionable suggestion."
    )
    if recent_reflection:
        prompt += f"\nRecent topics:\n{recent_reflection}"
    return prompt


def _llm_enabled() -> bool:
    return os.getenv("MENTOR_LLM_ENABLED", "true").lower() == "true"


def _get_memory(user: User) -> MentorMemory:
    memory, _ = MentorMemory.objects.get_or_create(user=user)
    if "entries" not in memory.notes:
        memory.notes["entries"] = []
    return memory


def _update_memory(memory: MentorMemory, question: str, answer: str, sentiment: str) -> None:
    notes = memory.notes or {}
    entries = notes.get("entries", [])
    entries.append(
        {
            "question": question,
            "answer": answer,
            "sentiment": sentiment,
            "timestamp": timezone.now().isoformat(),
        }
    )
    notes["entries"] = entries[-20:]
    memory.notes = notes
    memory.last_summary = _summarize_entries(notes["entries"])
    memory.save(update_fields=["notes", "last_summary", "updated_at"])


def _summarize_entries(entries: list[dict]) -> str:
    if not entries:
        return ""
    sentiments = [entry.get("sentiment") for entry in entries if entry.get("sentiment")]
    sentiment_summary = ", ".join(sentiments[-5:]) or "neutral"
    recent_topics = [entry.get("question", "")[:40] for entry in entries[-3:]]
    topics = "; ".join(topic for topic in recent_topics if topic)
    base = f"Recent sentiments: {sentiment_summary}."
    if topics:
        base += f" Topics touched: {topics}."
    return base
