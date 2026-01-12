from __future__ import annotations

import logging
from typing import Any, Dict, List

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mentor.models import MentorMessage, MentorSession
from apps.mentor.serializers import (
    DailyEntryRequestSerializer,
    DailyHistoryParamsSerializer,
    MentorChatRequestSerializer,
    MentorMessageSerializer,
)
from apps.mentor.services import llm_client, memory_manager, prompt_builder, safety
from apps.mentor.tasks import mentor_daily_entry_task
from apps.core_platform.async_mode import should_run_async
from apps.core_platform.rate_limit import is_rate_limited

logger = logging.getLogger(__name__)


def _mentor_feature_enabled() -> bool:
    feature_flags = getattr(settings, "FEATURE_FLAGS", {})
    return feature_flags.get("mentor_llm", True)


class MentorChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "mentor"

    def post(self, request, *args, **kwargs) -> Response:  # type: ignore[override]
        serializer = MentorChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        user = request.user

        user_message: str = validated["message"]
        mode: str = validated.get("mode") or MentorSession.MODE_CHAT
        if mode == MentorSession.MODE_DEFAULT:
            mode = MentorSession.MODE_CHAT
        language: str | None = validated.get("language") or None

        pre_flags = safety.preprocess_user_message(user_message)

        if not _mentor_feature_enabled():
            mentor_reply_raw = (
                "Mentor chat is temporarily unavailable. Please try again soon."
            )
        else:
            history = memory_manager.load_conversation_history(user, mode=mode)
            messages = prompt_builder.build_messages(
                user=user,
                language=language,
                mode=mode,
                history=history,
                user_text=user_message,
            )
            mentor_reply_raw = llm_client.chat(messages)

        mentor_reply, post_flags = safety.postprocess_mentor_reply(mentor_reply_raw)

        session = MentorSession.objects.create(
            user=user,
            question=user_message,
            answer=mentor_reply,
            sentiment="",
            mode=mode,
            language=language,
            active=True,
        )
        user_message_obj = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.USER,
            content=user_message,
            meta={"safety": pre_flags} if pre_flags else None,
        )
        mentor_message_obj = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.MENTOR,
            content=mentor_reply,
            meta={"safety": post_flags} if post_flags else None,
        )

        memory_manager.store_conversation(user, session, user_message, mentor_reply)

        payload: Dict[str, Any] = {
            "session_id": session.id,
            "user_message_id": user_message_obj.id,
            "mentor_message_id": mentor_message_obj.id,
            "mentor_reply": mentor_reply,
            "mode": mode,
            "language": language,
            "meta": {"user_flags": pre_flags, "mentor_flags": post_flags},
        }
        return Response(payload, status=status.HTTP_200_OK)


class DailyEntryView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "mentor"

    def post(self, request, *args, **kwargs) -> Response:  # type: ignore[override]
        serializer = DailyEntryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        user = request.user
        entry_text: str = validated["text"]
        entry_date = validated.get("date") or timezone.localdate()
        language: str | None = validated.get("language") or None
        mode = MentorSession.MODE_DAILY

        pre_flags = safety.preprocess_user_message(entry_text)

        if is_rate_limited(f"mentor:user:{user.id}", settings.MENTOR_RPS_USER, 1) or is_rate_limited(
            "mentor:global",
            settings.MENTOR_RPS_GLOBAL,
            1,
        ):
            return Response({"detail": "Rate limit exceeded."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        session = (
            MentorSession.objects.filter(
                user=user,
                mode=mode,
                date=entry_date,
            )
            .order_by("-created_at")
            .first()
        )

        if should_run_async(request):
            if session is None:
                session = MentorSession.objects.create(
                    user=user,
                    question=entry_text,
                    answer="",
                    sentiment="",
                    mode=mode,
                    language=language,
                    active=True,
                    date=entry_date,
                )
            else:
                session.question = entry_text
                session.language = language or session.language
                session.date = entry_date
                session.save(update_fields=["question", "language", "date", "updated_at"])

            user_message_obj = MentorMessage.objects.create(
                session=session,
                role=MentorMessage.Role.USER,
                content=entry_text,
                meta={"safety": pre_flags} if pre_flags else None,
            )
            task_result = mentor_daily_entry_task.apply_async(
                args=[session.id, user_message_obj.id],
                kwargs={"language": language},
            )
            meta = user_message_obj.meta or {}
            meta.update({"task_id": task_result.id, "task_version": "v1"})
            user_message_obj.meta = meta
            user_message_obj.save(update_fields=["meta", "updated_at"])

            return Response(
                {
                    "session_id": session.id,
                    "date": str(entry_date),
                    "entry": entry_text,
                    "message_id": user_message_obj.id,
                    "task_id": task_result.id,
                    "language": language,
                    "meta": {"user_flags": pre_flags},
                },
                status=status.HTTP_202_ACCEPTED,
            )

        if not _mentor_feature_enabled():
            mentor_reply_raw = (
                "Daily mentor is temporarily unavailable. Please try again soon."
            )
        else:
            history = memory_manager.load_conversation_history(
                user=user, mode=mode, session=session
            )
            messages = prompt_builder.build_messages(
                user=user,
                language=language,
                mode=mode,
                history=history,
                user_text=entry_text,
            )
            mentor_reply_raw = llm_client.chat(messages)

        mentor_reply, post_flags = safety.postprocess_mentor_reply(mentor_reply_raw)

        if session is None:
            session = MentorSession.objects.create(
                user=user,
                question=entry_text,
                answer=mentor_reply,
                sentiment="",
                mode=mode,
                language=language,
                active=True,
                date=entry_date,
            )
        else:
            session.question = entry_text
            session.answer = mentor_reply
            session.language = language or session.language
            session.date = entry_date
            session.save(update_fields=["question", "answer", "language", "date", "updated_at"])

        user_message_obj = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.USER,
            content=entry_text,
            meta={"safety": pre_flags} if pre_flags else None,
        )
        mentor_message_obj = MentorMessage.objects.create(
            session=session,
            role=MentorMessage.Role.MENTOR,
            content=mentor_reply,
            meta={"safety": post_flags} if post_flags else None,
        )

        memory_manager.store_conversation(user, session, entry_text, mentor_reply)

        payload: Dict[str, Any] = {
            "session_id": session.id,
            "date": str(entry_date),
            "entry": entry_text,
            "reply": mentor_reply,
            "messages": [
                {"role": "user", "content": entry_text, "id": user_message_obj.id},
                {"role": "assistant", "content": mentor_reply, "id": mentor_message_obj.id},
            ],
            "language": language,
            "meta": {"user_flags": pre_flags, "mentor_flags": post_flags},
        }
        return Response(payload, status=status.HTTP_200_OK)


class DailyHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:  # type: ignore[override]
        params = DailyHistoryParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        limit = params.validated_data.get("limit") or 7

        sessions = (
            MentorSession.objects.filter(user=request.user, mode=MentorSession.MODE_DAILY)
            .order_by("-date", "-created_at")[:limit]
        )

        history: List[Dict[str, Any]] = []
        for session in sessions:
            entry_preview = (session.question or "")[:120]
            reply_preview = (session.answer or "")[:120]
            history.append(
                {
                    "session_id": session.id,
                    "date": str(session.date) if session.date else None,
                    "entry_preview": entry_preview,
                    "reply_preview": reply_preview,
                }
            )

        return Response({"results": history}, status=status.HTTP_200_OK)


class DailySessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id: int, *args, **kwargs) -> Response:  # type: ignore[override]
        try:
            session = MentorSession.objects.get(
                id=session_id, user=request.user, mode=MentorSession.MODE_DAILY
            )
        except MentorSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        messages = (
            MentorMessage.objects.filter(session=session)
            .order_by("created_at")
            .values("id", "role", "content", "created_at")
        )

        payload = {
            "session_id": session.id,
            "date": str(session.date) if session.date else None,
            "language": session.language,
            "messages": list(messages),
        }
        return Response(payload, status=status.HTTP_200_OK)


class MentorHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MentorMessageSerializer

    def get_queryset(self):  # type: ignore[override]
        return (
            MentorMessage.objects.filter(session__user=self.request.user)
            .select_related("session")
            .order_by("-created_at")
        )


class MentorTaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: str, *args, **kwargs) -> Response:  # type: ignore[override]
        message = (
            MentorMessage.objects.filter(
                session__user=request.user,
                meta__task_id=task_id,
                role__in=[MentorMessage.Role.ASSISTANT, MentorMessage.Role.MENTOR],
            )
            .select_related("session")
            .order_by("-created_at")
            .first()
        )
        if message:
            session = message.session
            return Response(
                {
                    "task_id": task_id,
                    "status": "ready",
                    "message": MentorMessageSerializer(message).data,
                    "session": {
                        "id": session.id,
                        "mode": session.mode,
                        "date": str(session.date) if session.date else None,
                        "metadata": session.metadata,
                    },
                },
                status=status.HTTP_200_OK,
            )

        pending = MentorMessage.objects.filter(
            session__user=request.user,
            meta__task_id=task_id,
        ).exists()
        if pending:
            return Response({"task_id": task_id, "status": "pending"}, status=status.HTTP_200_OK)

        return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
