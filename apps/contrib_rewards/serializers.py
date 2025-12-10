from __future__ import annotations

from rest_framework import serializers

from apps.contrib_rewards.models import MonthlyRewardSnapshot, Payout, RewardEvent


class RewardEventSerializer(serializers.ModelSerializer):
    contributor = serializers.SerializerMethodField()

    class Meta:
        model = RewardEvent
        fields = ("id", "event_type", "points", "occurred_at", "reference", "metadata", "notes", "contributor")
        read_only_fields = fields

    def get_contributor(self, obj):  # pragma: no cover - trivial mapping
        contributor = obj.contributor
        return {
            "id": contributor.id,
            "user_id": contributor.user_id,
            "github_username": contributor.github_username,
        }


class PayoutSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source="snapshot.period", read_only=True)

    class Meta:
        model = Payout
        fields = ("id", "period", "points", "amount_cents", "status", "metadata")
        read_only_fields = fields


class MonthlyRewardSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyRewardSnapshot
        fields = (
            "id",
            "period",
            "revenue_cents",
            "costs_cents",
            "contributor_pool_cents",
            "total_points",
            "total_events",
            "ledger_hash",
            "dispute_window_ends_at",
        )
        read_only_fields = fields
