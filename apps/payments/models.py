from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import BaseModel


class Plan(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    price_cents = models.PositiveIntegerField()
    interval = models.CharField(max_length=16, default="month")
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    external_price_id = models.CharField(max_length=96, blank=True, null=True)

    class Meta:
        ordering = ["price_cents"]


class Subscription(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELED = "canceled", "Canceled"
        INCOMPLETE = "incomplete", "Incomplete"
        PAST_DUE = "past_due", "Past Due"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INCOMPLETE)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    external_customer_id = models.CharField(max_length=96, blank=True, null=True)
    external_subscription_id = models.CharField(max_length=96, blank=True, null=True)

    class Meta:
        unique_together = ("user", "plan")


class Wallet(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="wallet")
    balance_cents = models.IntegerField(default=0)
    external_customer_id = models.CharField(max_length=96, blank=True, null=True, unique=True)


class GiftType(BaseModel):
    class Kind(models.TextChoices):
        STATIC = "static", "Static"
        ANIMATED = "animated", "Animated"

    key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    name = models.CharField(max_length=64, unique=True)
    price_cents = models.PositiveIntegerField()
    price_slc_cents = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.STATIC)
    media_file = models.ImageField(
        upload_to="gifts/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["png"])],
        help_text="Upload a .png file (optional).",
    )
    art_url = models.CharField(max_length=500, blank=True, default="")
    media_url = models.CharField(max_length=500, blank=True, default="")
    animation_file = models.FileField(
        upload_to="gifts/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["json"])],
        help_text="Upload a .json Lottie file (optional).",
    )
    animation_url = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    effects = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["price_cents"]

    def save(self, *args, **kwargs):  # type: ignore[override]
        needs_media = bool(self.media_file and not self.media_url)
        needs_animation = bool(self.animation_file and not self.animation_url)
        super().save(*args, **kwargs)
        updates = {}
        if needs_media and self.media_file and not self.media_url:
            updates["media_url"] = self.media_file.url
        if needs_animation and self.animation_file and not self.animation_url:
            updates["animation_url"] = self.animation_file.url
        if updates:
            GiftType.objects.filter(pk=self.pk).update(**updates)
            for key, value in updates.items():
                setattr(self, key, value)


class PaymentEvent(BaseModel):
    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        IPAY = "ipay", "iPay"
        BTCPAY = "btcpay", "BTCPay"
        APPLE_IAP = "apple_iap", "Apple IAP"
        GOOGLE_IAP = "google_iap", "Google IAP"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        MINTED = "minted", "Minted"
        FAILED = "failed", "Failed"

    provider = models.CharField(max_length=32, choices=Provider.choices)
    provider_event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=64, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_events")
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    minted_coin_event = models.ForeignKey(
        "coin.CoinEvent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payment_events",
    )
    raw_body_hash = models.CharField(max_length=64)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("provider", "provider_event_id")


def generate_payment_reference() -> str:
    return uuid.uuid4().hex


class PaymentCheckout(BaseModel):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    provider = models.CharField(max_length=32, choices=PaymentEvent.Provider.choices)
    reference = models.CharField(max_length=64, unique=True, default=generate_payment_reference)
    provider_reference = models.CharField(max_length=128, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_checkouts")
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CREATED)
