from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import GiftType, Plan, Subscription, Wallet


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "price_cents", "interval", "features", "is_active"]
        read_only_fields = ["id", "is_active"]


class GiftTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftType
        fields = ["id", "name", "price_cents", "art_url", "metadata"]


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "balance_cents", "created_at", "updated_at"]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "current_period_start",
            "current_period_end",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubscriptionCreateSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate_plan_id(self, value: int) -> int:
        if not Plan.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Plan not available")
        return value

    def save(self) -> Subscription:
        request = self.context["request"]
        plan = Plan.objects.get(id=self.validated_data["plan_id"])
        subscription, _ = Subscription.objects.update_or_create(
            user=request.user,
            plan=plan,
            defaults={
                "status": Subscription.Status.ACTIVE,
                "current_period_start": timezone.now(),
                "current_period_end": timezone.now() + timedelta(days=30),
            },
        )
        Wallet.objects.get_or_create(user=request.user)
        return subscription
