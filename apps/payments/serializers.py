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
    art_url = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    animation_url = serializers.SerializerMethodField()

    class Meta:
        model = GiftType
        fields = [
            "id",
            "key",
            "name",
            "kind",
            "price_cents",
            "price_slc_cents",
            "art_url",
            "media_url",
            "animation_url",
            "is_active",
            "effects",
            "metadata",
        ]

    def _absolute_url(self, url: str) -> str:
        if not url:
            return url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        public_base = getattr(settings, "PUBLIC_BASE_URL", "") or ""
        if public_base:
            if url.startswith("/"):
                return f"{public_base}{url}"
            return f"{public_base}/{url}"
        return url

    def get_art_url(self, obj: GiftType) -> str:
        return self._absolute_url(obj.art_url or "")

    def get_media_url(self, obj: GiftType) -> str:
        if obj.media_file and getattr(obj.media_file, "url", ""):
            return self._absolute_url(obj.media_file.url)
        return self._absolute_url(obj.media_url or "")

    def get_animation_url(self, obj: GiftType) -> str:
        if obj.animation_file and getattr(obj.animation_file, "url", ""):
            return self._absolute_url(obj.animation_file.url)
        return self._absolute_url(obj.animation_url or "")

    def to_representation(self, instance):  # type: ignore[override]
        from apps.payments.effects import normalize_gift_effects

        data = super().to_representation(instance)
        data["effects"] = normalize_gift_effects(data.get("effects"))
        return data


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


class BtcPayCheckoutCreateSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1)
    currency = serializers.CharField(max_length=8)

    def validate_currency(self, value: str) -> str:
        currency = value.strip().upper()
        allowed = getattr(settings, "BTCPAY_ALLOWED_CURRENCIES", []) or []
        if allowed and currency not in allowed:
            raise serializers.ValidationError("Currency not supported for BTCPay.")
        return currency

    def save(self) -> PaymentCheckout:
        request = self.context["request"]
        return PaymentCheckout.objects.create(
            provider=PaymentEvent.Provider.BTCPAY,
            user=request.user,
            amount_cents=self.validated_data["amount_cents"],
            currency=self.validated_data["currency"],
        )


class IapVerifySerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=["ios", "android"])
    product_id = serializers.CharField(max_length=128)
    transaction_id = serializers.CharField(max_length=128)
    receipt = serializers.CharField(required=False, allow_blank=True)
    purchase_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        platform = attrs.get("platform")
        if platform == "ios" and not attrs.get("receipt"):
            raise serializers.ValidationError({"receipt": "Receipt is required for iOS."})
        if platform == "android" and not attrs.get("purchase_token"):
            raise serializers.ValidationError({"purchase_token": "Purchase token is required for Android."})
        return attrs
