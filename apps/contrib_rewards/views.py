from __future__ import annotations

from rest_framework import permissions, viewsets

from apps.contrib_rewards.models import MonthlyRewardSnapshot, Payout, RewardEvent
from apps.contrib_rewards.serializers import (
    MonthlyRewardSnapshotSerializer,
    PayoutSerializer,
    RewardEventSerializer,
)


class RewardEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RewardEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        user = self.request.user
        return (
            RewardEvent.objects.select_related("contributor", "contributor__user")
            .filter(contributor__user=user)
            .order_by("-occurred_at", "-created_at")
        )


class PayoutViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):  # type: ignore[override]
        user = self.request.user
        return (
            Payout.objects.select_related("contributor", "snapshot")
            .filter(contributor__user=user)
            .order_by("-snapshot__period", "contributor_id")
        )


class MonthlyRewardSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MonthlyRewardSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = MonthlyRewardSnapshot.objects.all().order_by("-period")
