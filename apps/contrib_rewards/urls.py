from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.contrib_rewards.views import (
    GitHubRewardsWebhookView,
    MonthlyRewardSnapshotViewSet,
    PayoutViewSet,
    RewardEventViewSet,
)

router = DefaultRouter()
router.register(r"contrib-rewards/events", RewardEventViewSet, basename="contrib-reward-events")
router.register(r"contrib-rewards/payouts", PayoutViewSet, basename="contrib-reward-payouts")
router.register(r"contrib-rewards/snapshots", MonthlyRewardSnapshotViewSet, basename="contrib-reward-snapshots")

urlpatterns = [
    path("rewards/webhooks/github/", GitHubRewardsWebhookView.as_view(), name="rewards-github-webhook"),
    path("", include(router.urls)),
]
