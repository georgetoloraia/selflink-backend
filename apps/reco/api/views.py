from __future__ import annotations

from django.db.models import F
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.reco.models import SoulMatchScore
from apps.reco.scores import compute_soulmatch_scores
from apps.users.models import User
from apps.users.serializers import UserSerializer


class SoulMatchViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request: Request) -> Response:
        queryset = (
            SoulMatchScore.objects.filter(user=request.user)
            .select_related("target")
            .order_by("-score")[:20]
        )
        data = [
            {
                "target": UserSerializer(item.target, context={"request": request}).data,
                "score": item.score,
                "breakdown": item.breakdown,
            }
            for item in queryset
        ]
        return Response(data)

    @action(detail=False, methods=["post"], url_path="refresh")
    def refresh(self, request: Request) -> Response:
        candidates = User.objects.exclude(id=request.user.id)[:100]
        compute_soulmatch_scores(request.user, candidates)
        return Response({"status": "refreshed"})
