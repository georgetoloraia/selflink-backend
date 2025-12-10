from __future__ import annotations

import random

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.matching.serializers import SoulmatchResultSerializer, SoulmatchUserSerializer
from apps.matching.services.soulmatch import calculate_soulmatch
from apps.matching.tasks import calculate_soulmatch_task
from apps.users.models import User


class SoulmatchWithView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "matching"

    def get(self, request, user_id: int):
        current_user: User = request.user
        if current_user.id == user_id:
            return Response({"detail": "Cannot compute SoulMatch with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = calculate_soulmatch_task.apply_async(args=[current_user.id, target.id]).get(timeout=30)
        except Exception:
            result = calculate_soulmatch(current_user, target)
        payload = {"user": SoulmatchUserSerializer(target).data, **result}
        return Response(payload, status=status.HTTP_200_OK)


class SoulmatchRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "matching"

    def get(self, request):
        current_user: User = request.user
        candidates = list(User.objects.exclude(id=current_user.id).order_by("id")[:50])
        random.shuffle(candidates)

        recommendations = []
        for candidate in candidates:
            # TODO: batch this via Celery if we keep computing many matches per request.
            result = calculate_soulmatch(current_user, candidate)
            recommendations.append({"user": SoulmatchUserSerializer(candidate).data, **result})

        recommendations.sort(key=lambda item: item["score"], reverse=True)
        top_results = recommendations[:20]
        serializer = SoulmatchResultSerializer(top_results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
