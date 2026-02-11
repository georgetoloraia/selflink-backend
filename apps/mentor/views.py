from __future__ import annotations

from datetime import date

from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services.llama_client import AIMentorError, generate_llama_response
from apps.ai.services.mentor import (
    DAILY_MENTOR_SYSTEM_PROMPT,
    NATAL_MENTOR_SYSTEM_PROMPT,
    SOULMATCH_MENTOR_SYSTEM_PROMPT,
    build_daily_prompt,
    build_natal_prompt,
    build_soulmatch_prompt,
)
from apps.astro.services.transits import get_today_transits
from apps.core_platform.async_mode import should_run_async_default
from apps.matching.services.soulmatch import calculate_soulmatch
from apps.mentor.models import MentorMessageRole
from apps.users.models import User
from .models import DailyTask, MentorMessage, MentorProfile, MentorSession
from .serializers import DailyTaskSerializer, MentorAskSerializer, MentorProfileSerializer, MentorSessionSerializer
from .services import generate_mentor_reply
from .tasks import mentor_daily_mentor_task, mentor_natal_generate_task, mentor_soulmatch_generate_task


@method_decorator(ratelimit(key="user", rate="30/min", method="POST", block=True), name="ask")
class MentorSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MentorSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "mentor"

    def get_queryset(self):  # type: ignore[override]
        return MentorSession.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=False, methods=["post"], url_path="ask")
    def ask(self, request: Request) -> Response:
        serializer = MentorAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["text"]
        api_key = request.headers.get("X-LLM-Key")
        answer, sentiment = generate_mentor_reply(request.user, text, api_key=api_key)
        session = MentorSession.objects.create(
            user=request.user,
            question=text,
            answer=answer,
            sentiment=sentiment,
        )
        return Response(MentorSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class DailyTaskViewSet(viewsets.ModelViewSet):
    serializer_class = DailyTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        return DailyTask.objects.filter(user=self.request.user).order_by("due_date")

    def perform_create(self, serializer: DailyTaskSerializer) -> None:  # type: ignore[override]
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request: Request) -> Response:
        today: date = timezone.localdate()
        task = (
            DailyTask.objects.filter(user=request.user, due_date=today)
            .order_by("-created_at")
            .first()
        )
        if not task:
            task = DailyTask.objects.create(
                user=request.user,
                due_date=today,
                task="Take five conscious breaths and note one feeling that arises.",
            )
        return Response(self.get_serializer(task).data)


class MentorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = MentorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "mentor"

    def get_queryset(self):  # type: ignore[override]
        return MentorProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer: MentorProfileSerializer) -> None:  # type: ignore[override]
        serializer.save(user=self.request.user)

    def perform_update(self, serializer: MentorProfileSerializer) -> None:  # type: ignore[override]
        serializer.save(user=self.request.user)


class NatalMentorView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "mentor"

    def post(self, request: Request) -> Response:
        user = request.user
        chart = getattr(user, "natal_chart", None)
        if chart is None:
            return Response(
                {"detail": "No natal chart found. Create your chart via /api/v1/astro/natal/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key = request.headers.get("X-LLM-Key")
        if should_run_async_default(request, default_async=True):
            session = MentorSession.objects.create(
                user=user,
                mode=MentorSession.MODE_NATAL_MENTOR,
                language=None,
                active=True,
                metadata={"natal_chart_id": chart.id},
                question="Natal mentor request",
            )
            user_message_obj = MentorMessage.objects.create(
                session=session,
                role=MentorMessageRole.USER,
                content="Natal mentor request",
                meta={"natal_chart_id": chart.id},
            )
            task_result = mentor_natal_generate_task.apply_async(
                args=[session.id, user_message_obj.id, chart.id],
                kwargs={"api_key": api_key},
            )
            meta = user_message_obj.meta or {}
            meta.update({"task_id": task_result.id, "task_version": "v1"})
            user_message_obj.meta = meta
            user_message_obj.save(update_fields=["meta", "updated_at"])
            return Response(
                {
                    "session_id": session.id,
                    "message_id": user_message_obj.id,
                    "task_id": task_result.id,
                    "task_status_url": f"/api/v1/mentor/task-status/{task_result.id}/",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        prompt = build_natal_prompt(user, chart)
        try:
            mentor_text = generate_llama_response(NATAL_MENTOR_SYSTEM_PROMPT, prompt, api_key=api_key)
        except AIMentorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"mentor_text": mentor_text, "generated_at": timezone.now()}, status=status.HTTP_200_OK)


class SoulmatchMentorView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "mentor"

    def get(self, request: Request, user_id: int) -> Response:
        user: User = request.user
        if user.id == user_id:
            return Response({"detail": "Cannot mentor match against yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        api_key = request.headers.get("X-LLM-Key")
        if should_run_async_default(request, default_async=True):
            session = MentorSession.objects.create(
                user=user,
                mode=MentorSession.MODE_SOULMATCH,
                language=None,
                active=True,
                metadata={"target_user_id": target.id},
                question=f"Soulmatch mentor request for user {target.id}",
            )
            user_message_obj = MentorMessage.objects.create(
                session=session,
                role=MentorMessageRole.USER,
                content=f"Soulmatch mentor request for user {target.id}",
                meta={"target_user_id": target.id},
            )
            task_result = mentor_soulmatch_generate_task.apply_async(
                args=[session.id, user_message_obj.id, target.id],
                kwargs={"api_key": api_key},
            )
            meta = user_message_obj.meta or {}
            meta.update({"task_id": task_result.id, "task_version": "v1"})
            user_message_obj.meta = meta
            user_message_obj.save(update_fields=["meta", "updated_at"])
            return Response(
                {
                    "session_id": session.id,
                    "message_id": user_message_obj.id,
                    "task_id": task_result.id,
                    "task_status_url": f"/api/v1/mentor/task-status/{task_result.id}/",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        results = calculate_soulmatch(user, target)
        prompt = build_soulmatch_prompt(user, target, results)
        try:
            mentor_text = generate_llama_response(
                SOULMATCH_MENTOR_SYSTEM_PROMPT,
                prompt,
                max_tokens=256,
                timeout=30,
                api_key=api_key,
            )
        except AIMentorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        payload = {**results, "mentor_text": mentor_text, "user": {"id": target.id, "handle": target.handle, "name": target.name}}
        return Response(payload, status=status.HTTP_200_OK)


class DailyMentorView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "mentor"

    def get(self, request: Request) -> Response:
        user: User = request.user
        chart = getattr(user, "natal_chart", None)
        if chart is None:
            return Response(
                {"detail": "No natal chart found. Create your chart via /api/v1/astro/natal/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        api_key = request.headers.get("X-LLM-Key")
        if should_run_async_default(request, default_async=True):
            entry_date = timezone.localdate()
            session = MentorSession.objects.create(
                user=user,
                mode=MentorSession.MODE_DAILY_MENTOR,
                language=None,
                active=True,
                date=entry_date,
                metadata={"date": str(entry_date)},
                question="Daily mentor request",
            )
            user_message_obj = MentorMessage.objects.create(
                session=session,
                role=MentorMessageRole.USER,
                content="Daily mentor request",
                meta={"date": str(entry_date)},
            )
            task_result = mentor_daily_mentor_task.apply_async(
                args=[session.id, user_message_obj.id],
                kwargs={"api_key": api_key},
            )
            meta = user_message_obj.meta or {}
            meta.update({"task_id": task_result.id, "task_version": "v1"})
            user_message_obj.meta = meta
            user_message_obj.save(update_fields=["meta", "updated_at"])
            return Response(
                {
                    "session_id": session.id,
                    "message_id": user_message_obj.id,
                    "task_id": task_result.id,
                    "date": str(entry_date),
                    "task_status_url": f"/api/v1/mentor/task-status/{task_result.id}/",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        birth_data = getattr(chart, "birth_data", None)
        transits = None
        if birth_data:
            try:
                transits = get_today_transits(birth_data.latitude, birth_data.longitude)
            except Exception:
                transits = None
        prompt = build_daily_prompt(user, chart, transits)
        try:
            mentor_text = generate_llama_response(DAILY_MENTOR_SYSTEM_PROMPT, prompt, api_key=api_key)
        except AIMentorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"date": timezone.localdate(), "messages": mentor_text.split("\n")})
