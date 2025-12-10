from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model

from apps.ai.services.llama_client import generate_llama_response
from apps.mentor.services import generate_mentor_reply
from apps.mentor.services.llm_client import full_completion

User = get_user_model()


@shared_task
def generate_mentor_reply_task(user_id: int, question: str, api_key: str | None = None) -> dict[str, str]:
    user = User.objects.get(id=user_id)
    answer, sentiment = generate_mentor_reply(user, question, api_key=api_key)
    return {"answer": answer, "sentiment": sentiment}


@shared_task
def mentor_full_completion_task(full_prompt: str, max_chars: int = 8000) -> str:
    return full_completion(full_prompt, max_chars=max_chars)


@shared_task
def llama_generate_task(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    timeout: float | None = None,
    api_key: str | None = None,
) -> str:
    return generate_llama_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        api_key=api_key,
    )
