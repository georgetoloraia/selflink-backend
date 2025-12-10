from __future__ import annotations

import logging
from typing import Any, Dict, List

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mentor.models import MentorMessage, MentorSession
from apps.mentor.services.llm_client import LLMError, build_prompt, full_completion
from apps.mentor.services.personality import get_persona_prompt
from apps.mentor.tasks import mentor_full_completion_task

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

        try:
            task_result = mentor_full_completion_task.apply_async(args=[full_prompt])
            reply_text = task_result.get(timeout=120)
        except Exception:
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
