from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditEvent
from apps.contrib_rewards.models import (
    ContributorProfile,
    LedgerEntryDirection,
    MonthlyRewardSnapshot,
    Payout,
    RewardEvent,
    RewardEventType,
)
from apps.contrib_rewards.serializers import (
    MonthlyRewardSnapshotSerializer,
    PayoutSerializer,
    RewardEventSerializer,
)
from apps.contrib_rewards.services.ledger import post_event_and_ledger_entries


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


class GitHubRewardsWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def post(self, request):
        secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", "")
        signature = request.headers.get("X-Hub-Signature-256", "")
        if secret:
            if not signature or not self._is_valid_signature(secret, request.body, signature):
                return Response({"detail": "Invalid signature."}, status=status.HTTP_403_FORBIDDEN)
        elif not settings.DEBUG:
            return Response({"detail": "Webhook secret not configured."}, status=status.HTTP_403_FORBIDDEN)

        if request.headers.get("X-GitHub-Event") != "pull_request":
            return Response(status=status.HTTP_204_NO_CONTENT)

        payload = request.data or {}
        action = payload.get("action")
        pr = payload.get("pull_request") or {}
        if action != "closed" or not pr.get("merged"):
            return Response(status=status.HTTP_204_NO_CONTENT)

        github_username = (pr.get("user") or {}).get("login") or (payload.get("sender") or {}).get("login")
        if not github_username:
            self._record_audit_event(
                actor_user=None,
                request=request,
                action="rewards.github.pr_merged.unmatched",
                object_id=str(pr.get("id") or pr.get("number") or ""),
                metadata={"reason": "missing_github_username"},
            )
            return Response(status=status.HTTP_202_ACCEPTED)

        contributor = (
            ContributorProfile.objects.select_related("user")
            .filter(github_username__iexact=github_username)
            .first()
        )
        if not contributor:
            self._record_audit_event(
                actor_user=None,
                request=request,
                action="rewards.github.pr_merged.unmatched",
                object_id=str(pr.get("id") or pr.get("number") or ""),
                metadata={"github_username": github_username},
            )
            return Response(status=status.HTTP_202_ACCEPTED)

        reference = f"PR-{pr.get('number') or pr.get('id') or 'unknown'}"
        if RewardEvent.objects.filter(
            contributor=contributor,
            event_type=RewardEventType.PR_MERGED,
            reference=reference,
        ).exists():
            return Response({"detail": "Already recorded."}, status=status.HTTP_200_OK)

        points = 10
        metadata = {
            "github_username": github_username,
            "pull_request": {
                "id": pr.get("id"),
                "number": pr.get("number"),
                "title": pr.get("title"),
                "url": pr.get("html_url"),
                "merged_at": pr.get("merged_at"),
            },
            "repository": (payload.get("repository") or {}).get("full_name"),
        }

        with transaction.atomic():
            reward_event = post_event_and_ledger_entries(
                event_type=RewardEventType.PR_MERGED,
                contributor=contributor,
                reference=reference,
                metadata=metadata,
                entries=[
                    {
                        "account": "platform:rewards_pool",
                        "amount": points,
                        "currency": "POINTS",
                        "direction": LedgerEntryDirection.DEBIT,
                    },
                    {
                        "account": f"user:{contributor.user_id}",
                        "amount": points,
                        "currency": "POINTS",
                        "direction": LedgerEntryDirection.CREDIT,
                    },
                ],
            )
            self._record_audit_event(
                actor_user=contributor.user,
                request=request,
                action="rewards.github.pr_merged",
                object_id=str(pr.get("id") or pr.get("number") or ""),
                metadata={**metadata, "reward_event_id": reward_event.id},
            )

        return Response({"detail": "Recorded."}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _is_valid_signature(secret: str, body: bytes, signature: str) -> bool:
        digest = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def _record_audit_event(actor_user, request, action: str, object_id: str, metadata: dict) -> None:
        AuditEvent.objects.create(
            actor_user=actor_user,
            actor_ip=GitHubRewardsWebhookView._client_ip(request),
            action=action,
            object_type="pull_request",
            object_id=object_id or "unknown",
            metadata=metadata or {},
        )

    @staticmethod
    def _client_ip(request) -> str | None:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
