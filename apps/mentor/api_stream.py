from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Generator, List

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.mentor.models import MentorMessage, MentorSession
from apps.mentor.services.llm_client import DEFAULT_TIMEOUT, LLMError, build_prompt, stream_completion
from apps.mentor.services.personality import get_persona_prompt
from apps.core_platform.rate_limit import is_rate_limited

logger = logging.getLogger(__name__)


def _sse_format(data: Dict[str, Any]) -> str:
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


class MentorChatStreamView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "mentor"

    def get(self, request, *args, **kwargs) -> StreamingHttpResponse:  # type: ignore[override]
        mode = request.query_params.get("mode") or MentorSession.DEFAULT_MODE
        language = request.query_params.get("language") or "en"
        user_message = (request.query_params.get("message") or "").strip()

        if not user_message:
            return StreamingHttpResponse(
                _sse_format({"event": "error", "detail": "Message is required."}),
                status=400,
                content_type="text/event-stream",
            )

        if is_rate_limited(f"mentor:user:{request.user.id}", settings.MENTOR_RPS_USER, 1) or is_rate_limited(
            "mentor:global",
            settings.MENTOR_RPS_GLOBAL,
            1,
        ):
            return StreamingHttpResponse(
                _sse_format({"event": "error", "detail": "Rate limit exceeded."}),
                status=429,
                content_type="text/event-stream",
            )

        def event_stream() -> Generator[str, None, None]:
            try:
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

                yield _sse_format({"event": "start", "session_id": session.id, "mode": mode})

                max_duration = DEFAULT_TIMEOUT
                started_at = time.monotonic()
                reply_parts: List[str] = []
                for chunk in stream_completion(full_prompt, timeout=max_duration):
                    if time.monotonic() - started_at > max_duration:
                        yield _sse_format({"event": "error", "detail": "Stream timed out."})
                        return
                    reply_parts.append(chunk)
                    yield _sse_format({"event": "token", "delta": chunk})

                full_reply = "".join(reply_parts)
                MentorMessage.objects.create(
                    session=session,
                    role=MentorMessage.Role.ASSISTANT,
                    content=full_reply,
                )
                yield _sse_format({"event": "end", "session_id": session.id})
            except LLMError as exc:
                logger.exception("Mentor LLM stream failed")
                yield _sse_format({"event": "error", "detail": str(exc)})
            except Exception:  # pragma: no cover - safeguard for streaming
                logger.exception("Unexpected mentor stream error")
                yield _sse_format({"event": "error", "detail": "Streaming failed."})

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
