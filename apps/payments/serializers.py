from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from .models import GiftType, PaymentCheckout, PaymentEvent, Plan, Subscription, Wallet
from .services import CheckoutSessionResult, create_checkout_session


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
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)

    def validate_plan_id(self, value: int) -> int:
        if not Plan.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Plan not available")
        return value

    def save(self) -> CheckoutSessionResult:
        request = self.context["request"]
        plan = Plan.objects.get(id=self.validated_data["plan_id"])
        success_url = self.validated_data.get("success_url") or getattr(
            settings, "PAYMENTS_CHECKOUT_SUCCESS_URL", "http://localhost:3000/payments/success"
        )
        cancel_url = self.validated_data.get("cancel_url") or getattr(
            settings, "PAYMENTS_CHECKOUT_CANCEL_URL", "http://localhost:3000/payments/cancel"
        )
        result = create_checkout_session(request.user, plan, success_url, cancel_url)
        return result


class IpayCheckoutCreateSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    currency = serializers.CharField(max_length=8)

    def validate_currency(self, value: str) -> str:
        currency = value.strip().upper()
        allowed = getattr(settings, "IPAY_ALLOWED_CURRENCIES", []) or []
        if allowed and currency not in allowed:
            raise serializers.ValidationError("Currency not supported for iPay.")
        return currency

    def save(self) -> PaymentCheckout:
        request = self.context["request"]
        return PaymentCheckout.objects.create(
            provider=PaymentEvent.Provider.IPAY,
            user=request.user,
            amount_cents=self.validated_data["amount_cents"],
            currency=self.validated_data["currency"],
        )


class StripeCheckoutCreateSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    currency = serializers.CharField(max_length=8)

    def validate_amount_cents(self, value: int) -> int:
        minimum = int(getattr(settings, "STRIPE_CHECKOUT_MIN_CENTS", 50))
        if value < minimum:
            raise serializers.ValidationError(f"Amount must be at least {minimum} cents.")
        return value

    def validate_currency(self, value: str) -> str:
        currency = value.strip().upper()
        allowed = getattr(settings, "STRIPE_ALLOWED_CURRENCIES", []) or []
        if allowed and currency not in allowed:
            raise serializers.ValidationError("Currency not supported for Stripe.")
        return currency

    def save(self) -> PaymentCheckout:
        request = self.context["request"]
        return PaymentCheckout.objects.create(
            provider=PaymentEvent.Provider.STRIPE,
            user=request.user,
            amount_cents=self.validated_data["amount_cents"],
            currency=self.validated_data["currency"],
        )
