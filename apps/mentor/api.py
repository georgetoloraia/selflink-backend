from __future__ import annotations

import logging
from typing import Any, Dict, List

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mentor.models import MentorMessage, MentorSession
from apps.mentor.services.llm_client import LLMError, build_prompt, full_completion
from apps.mentor.services.personality import get_persona_prompt
from apps.mentor.tasks import mentor_chat_generate_task
from apps.core_platform.async_mode import should_run_async
from apps.core_platform.rate_limit import is_rate_limited
from libs.llm import get_llm_client

logger = logging.getLogger(__name__)


class MentorChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "mentor"

    def post(self, request, *args, **kwargs) -> Response:  # type: ignore[override]
        payload: Dict[str, Any] = request.data or {}
        mode = payload.get("mode") or MentorSession.DEFAULT_MODE
        language = payload.get("language") or "en"
        user_message: str = (payload.get("message") or "").strip()

        if not user_message:
            return Response({"detail": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)

        if is_rate_limited(f"mentor:user:{request.user.id}", settings.MENTOR_RPS_USER, 1) or is_rate_limited(
            "mentor:global",
            settings.MENTOR_RPS_GLOBAL,
            1,
        ):
            return Response({"detail": "Rate limit exceeded."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        api_key = request.headers.get("X-LLM-Key")

        session = (
            MentorSession.objects.filter(
                user=request.user,
                mode=mode,
                language=language,
                active=True,
            )
            .order_by("-started_at")
            .first()
        )
        if session is None:
            session = MentorSession.objects.create(
                user=request.user,
                mode=mode,
                language=language,
                active=True,
                metadata={},
            )

        with transaction.atomic():
            user_message_obj = MentorMessage.objects.create(
                session=session,
                role=MentorMessage.Role.USER,
                content=user_message,
            )

        if should_run_async(request):
            task_result = mentor_chat_generate_task.apply_async(
                args=[session.id, user_message_obj.id],
                kwargs={"mode": mode, "language": language, "api_key": api_key},
            )
            user_message_obj.meta = {"task_id": task_result.id, "task_version": "v1"}
            user_message_obj.save(update_fields=["meta", "updated_at"])
            return Response(
                {
                    "session_id": session.id,
                    "mode": session.mode,
                    "message_id": user_message_obj.id,
                    "task_id": task_result.id,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        user_profile_summary = f"id={request.user.id}, email={getattr(request.user, 'email', '')}"
        astro_summary = None

        recent_messages = list(
            session.messages.exclude(id=user_message_obj.id)
            .order_by("-created_at")
            .values("role", "content")[:10]
        )
        recent_messages.reverse()
        history: List[Dict[str, str]] = [
            {"role": msg["role"], "content": msg["content"]} for msg in recent_messages
        ]

        system_prompt = get_persona_prompt(language)
        full_prompt = build_prompt(
            system_prompt=system_prompt,
            mode=mode,
            user_profile_summary=user_profile_summary,
            astro_summary=astro_summary,
            history=history,
            user_message=user_message,
        )

        if api_key:
            try:
                llm = get_llm_client(overrides={"api_key": api_key})
                reply_text = llm.complete(system_prompt="", user_prompt=full_prompt)
            except Exception:
                try:
                    reply_text = full_completion(full_prompt)
                except LLMError as exc:  # pragma: no cover - depends on runtime LLM availability
                    logger.exception("Mentor LLM full completion failed")
                    return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        else:
            try:
                reply_text = full_completion(full_prompt)
            except LLMError as exc:  # pragma: no cover - depends on runtime LLM availability
                logger.exception("Mentor LLM full completion failed")
                return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.ASSISTANT,
            content=reply_text,
        )

        return Response(
            {"session_id": session.id, "mode": session.mode, "message": reply_text},
            status=status.HTTP_200_OK,
        )
