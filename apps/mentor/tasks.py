from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.ai.services.llama_client import generate_llama_response
from apps.ai.services.mentor import (
    DAILY_MENTOR_SYSTEM_PROMPT,
    NATAL_MENTOR_SYSTEM_PROMPT,
    SOULMATCH_MENTOR_SYSTEM_PROMPT,
    build_daily_prompt,
    build_natal_prompt,
    build_soulmatch_prompt,
)
from apps.astro.models import NatalChart
from apps.astro.services.transits import get_today_transits
from apps.matching.services.soulmatch import calculate_soulmatch
from apps.mentor.models import MentorMessage, MentorSession
from apps.mentor.services import generate_mentor_reply, llm_client
from apps.mentor.services import memory_manager, prompt_builder, safety
from apps.mentor.services.llm_client import build_prompt, full_completion
from apps.mentor.services.personality import get_persona_prompt
from libs.llm import get_llm_client

User = get_user_model()

DEFAULT_MENTOR_ERROR = "Mentor is unavailable right now. Please try again shortly."


def _mentor_feature_enabled() -> bool:
    feature_flags = getattr(settings, "FEATURE_FLAGS", {})
    return feature_flags.get("mentor_llm", True)


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


@shared_task(bind=True)
def mentor_chat_generate_task(
    self,
    session_id: int,
    user_message_id: int,
    mode: str | None = None,
    language: str | None = None,
    api_key: str | None = None,
    task_version: str = "v1",
) -> dict[str, object]:
    session = MentorSession.objects.select_related("user").get(id=session_id)
    user_message = MentorMessage.objects.get(id=user_message_id, session=session)

    existing = MentorMessage.objects.filter(
        session=session,
        role=MentorMessage.Role.ASSISTANT,
        meta__request_id=user_message_id,
        meta__task_version=task_version,
    ).first()
    if existing:
        return {"session_id": session.id, "message_id": existing.id, "reply": existing.content}

    mode = mode or session.mode
    language = language or session.language or "en"

    recent_messages = list(
        session.messages.exclude(id=user_message_id)
        .order_by("-created_at")
        .values("role", "content")[:10]
    )
    recent_messages.reverse()
    history = [{"role": msg["role"], "content": msg["content"]} for msg in recent_messages]

    user_profile_summary = f"id={session.user.id}, email={getattr(session.user, 'email', '')}"
    system_prompt = get_persona_prompt(language)
    full_prompt = build_prompt(
        system_prompt=system_prompt,
        mode=mode,
        user_profile_summary=user_profile_summary,
        astro_summary=None,
        history=history,
        user_message=user_message.content,
    )

    error = None
    try:
        if api_key:
            llm = get_llm_client(overrides={"api_key": api_key})
            reply_text = llm.complete(system_prompt="", user_prompt=full_prompt)
        else:
            reply_text = full_completion(full_prompt)
    except Exception:
        reply_text = DEFAULT_MENTOR_ERROR
        error = "llm_failure"

    task_id = self.request.id
    meta = {"request_id": user_message_id, "task_version": task_version, "task_id": task_id}
    if error:
        meta["error"] = error

    with transaction.atomic():
        assistant_message = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.ASSISTANT,
            content=reply_text,
            meta=meta,
        )

    return {"session_id": session.id, "message_id": assistant_message.id, "reply": reply_text}


@shared_task(bind=True)
def mentor_daily_entry_task(
    self,
    session_id: int,
    user_message_id: int,
    language: str | None = None,
    task_version: str = "v1",
) -> dict[str, object]:
    session = MentorSession.objects.select_related("user").get(id=session_id)
    user_message = MentorMessage.objects.get(id=user_message_id, session=session)

    existing = MentorMessage.objects.filter(
        session=session,
        role=MentorMessage.Role.MENTOR,
        meta__request_id=user_message_id,
        meta__task_version=task_version,
    ).first()
    if existing:
        return {"session_id": session.id, "message_id": existing.id, "reply": existing.content}

    if not _mentor_feature_enabled():
        mentor_reply_raw = "Daily mentor is temporarily unavailable. Please try again soon."
    else:
        history = memory_manager.load_conversation_history(user=session.user, mode=session.mode, session=session)
        messages = prompt_builder.build_messages(
            user=session.user,
            language=language,
            mode=session.mode,
            history=history,
            user_text=user_message.content,
        )
        mentor_reply_raw = llm_client.chat(messages)

    # Safety post-processing happens after LLM call; avoid duplicating in async path.
    if isinstance(mentor_reply_raw, tuple):
        mentor_reply, post_flags = mentor_reply_raw
    else:
        mentor_reply, post_flags = safety.postprocess_mentor_reply(mentor_reply_raw)

    session.question = user_message.content
    session.answer = mentor_reply
    session.language = language or session.language
    session.save(update_fields=["question", "answer", "language", "updated_at"])

    task_id = self.request.id
    meta = {"request_id": user_message_id, "task_version": task_version, "task_id": task_id}
    if post_flags:
        meta["safety"] = post_flags

    with transaction.atomic():
        mentor_message = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.MENTOR,
            content=mentor_reply,
            meta=meta,
        )

    memory_manager.store_conversation(session.user, session, user_message.content, mentor_reply)

    return {"session_id": session.id, "message_id": mentor_message.id, "reply": mentor_reply}


@shared_task(bind=True)
def mentor_natal_generate_task(
    self,
    session_id: int,
    user_message_id: int,
    chart_id: int,
    api_key: str | None = None,
    task_version: str = "v1",
) -> dict[str, object]:
    session = MentorSession.objects.select_related("user").get(id=session_id)
    user_message = MentorMessage.objects.get(id=user_message_id, session=session)

    error = None
    try:
        chart = NatalChart.objects.get(id=chart_id, user=session.user)
        prompt = build_natal_prompt(session.user, chart)
        reply_text = generate_llama_response(NATAL_MENTOR_SYSTEM_PROMPT, prompt, api_key=api_key)
    except Exception:
        reply_text = DEFAULT_MENTOR_ERROR
        error = "mentor_natal_failure"

    session.question = user_message.content
    session.answer = reply_text
    session.save(update_fields=["question", "answer", "updated_at"])

    task_id = self.request.id
    meta = {"request_id": user_message_id, "task_version": task_version, "task_id": task_id}
    if error:
        meta["error"] = error

    with transaction.atomic():
        mentor_message = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.MENTOR,
            content=reply_text,
            meta=meta,
        )

    return {"session_id": session.id, "message_id": mentor_message.id, "reply": reply_text}


@shared_task(bind=True)
def mentor_daily_mentor_task(
    self,
    session_id: int,
    user_message_id: int,
    api_key: str | None = None,
    task_version: str = "v1",
) -> dict[str, object]:
    session = MentorSession.objects.select_related("user").get(id=session_id)
    user_message = MentorMessage.objects.get(id=user_message_id, session=session)

    error = None
    try:
        chart = getattr(session.user, "natal_chart", None)
        if chart is None:
            raise ValueError("missing_chart")
        birth_data = getattr(chart, "birth_data", None)
        transits = None
        if birth_data:
            try:
                transits = get_today_transits(birth_data.latitude, birth_data.longitude)
            except Exception:
                transits = None
        prompt = build_daily_prompt(session.user, chart, transits)
        reply_text = generate_llama_response(DAILY_MENTOR_SYSTEM_PROMPT, prompt, api_key=api_key)
    except Exception as exc:
        reply_text = DEFAULT_MENTOR_ERROR
        error = "mentor_daily_failure"
        if str(exc) == "missing_chart":
            reply_text = "No natal chart found. Create your chart via /api/v1/astro/natal/ first."
            error = "missing_chart"

    session.question = user_message.content
    session.answer = reply_text
    session.save(update_fields=["question", "answer", "updated_at"])

    task_id = self.request.id
    meta = {"request_id": user_message_id, "task_version": task_version, "task_id": task_id}
    if error:
        meta["error"] = error

    with transaction.atomic():
        mentor_message = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.MENTOR,
            content=reply_text,
            meta=meta,
        )

    return {"session_id": session.id, "message_id": mentor_message.id, "reply": reply_text}


@shared_task(bind=True)
def mentor_soulmatch_generate_task(
    self,
    session_id: int,
    user_message_id: int,
    target_user_id: int,
    api_key: str | None = None,
    task_version: str = "v1",
) -> dict[str, object]:
    session = MentorSession.objects.select_related("user").get(id=session_id)
    user_message = MentorMessage.objects.get(id=user_message_id, session=session)

    error = None
    results: dict[str, object] | None = None
    try:
        target = User.objects.get(id=target_user_id)
        results = calculate_soulmatch(session.user, target)
        prompt = build_soulmatch_prompt(session.user, target, results)
        reply_text = generate_llama_response(
            SOULMATCH_MENTOR_SYSTEM_PROMPT,
            prompt,
            max_tokens=256,
            timeout=30,
            api_key=api_key,
        )
    except Exception:
        reply_text = DEFAULT_MENTOR_ERROR
        error = "mentor_soulmatch_failure"

    session.question = user_message.content
    session.answer = reply_text
    if results is not None:
        metadata = session.metadata or {}
        metadata.update({"target_user_id": target_user_id, "soulmatch": results})
        session.metadata = metadata
        session.save(update_fields=["question", "answer", "metadata", "updated_at"])
    else:
        session.save(update_fields=["question", "answer", "updated_at"])

    task_id = self.request.id
    meta = {"request_id": user_message_id, "task_version": task_version, "task_id": task_id}
    if error:
        meta["error"] = error

    with transaction.atomic():
        mentor_message = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.MENTOR,
            content=reply_text,
            meta=meta,
        )

    return {"session_id": session.id, "message_id": mentor_message.id, "reply": reply_text}
