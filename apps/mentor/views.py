from __future__ import annotations

from datetime import date

from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import DailyTask, MentorProfile, MentorSession
from .serializers import DailyTaskSerializer, MentorAskSerializer, MentorProfileSerializer, MentorSessionSerializer
from .services import generate_mentor_reply


@method_decorator(ratelimit(key="user", rate="30/min", method="POST", block=True), name="ask")
class MentorSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MentorSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        return MentorSession.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=False, methods=["post"], url_path="ask")
    def ask(self, request: Request) -> Response:
        serializer = MentorAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer, sentiment = generate_mentor_reply(request.user, serializer.validated_data["text"])
        session = MentorSession.objects.create(
            user=request.user,
            question=serializer.validated_data["text"],
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

    def get_queryset(self):  # type: ignore[override]
        return MentorProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer: MentorProfileSerializer) -> None:  # type: ignore[override]
        serializer.save(user=self.request.user)

    def perform_update(self, serializer: MentorProfileSerializer) -> None:  # type: ignore[override]
        serializer.save(user=self.request.user)
