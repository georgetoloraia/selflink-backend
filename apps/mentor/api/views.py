from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mentor.models import MentorMessage, MentorSession
from apps.mentor.serializers import MentorChatRequestSerializer, MentorMessageSerializer
from apps.mentor.services import llm_client, memory_manager, prompt_builder, safety

logger = logging.getLogger(__name__)


def _mentor_feature_enabled() -> bool:
    feature_flags = getattr(settings, "FEATURE_FLAGS", {})
    return feature_flags.get("mentor_llm", True)


class MentorChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:  # type: ignore[override]
        serializer = MentorChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        user = request.user

        user_message: str = validated["message"]
        mode: str = validated.get("mode") or "default"
        language: str | None = validated.get("language") or None

        pre_flags = safety.preprocess_user_message(user_message)

        if not _mentor_feature_enabled():
            mentor_reply_raw = (
                "Mentor chat is temporarily unavailable. Please try again soon."
            )
        else:
            messages = prompt_builder.build_messages(user, user_message, mode, language)
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


class MentorHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MentorMessageSerializer

    def get_queryset(self):  # type: ignore[override]
        return (
            MentorMessage.objects.filter(session__user=self.request.user)
            .select_related("session")
            .order_by("-created_at")
        )
