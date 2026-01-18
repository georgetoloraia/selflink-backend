from __future__ import annotations

import uuid

from django.conf import settings
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
    name = models.CharField(max_length=64, unique=True)
    price_cents = models.PositiveIntegerField()
    art_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["price_cents"]


class PaymentEvent(BaseModel):
    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        IPAY = "ipay", "iPay"

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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_checkouts")
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CREATED)
