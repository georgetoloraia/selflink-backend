from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class Plan(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    price_cents = models.PositiveIntegerField()
    interval = models.CharField(max_length=16, default="month")
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_cents"]


class Subscription(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELED = "canceled", "Canceled"
        INCOMPLETE = "incomplete", "Incomplete"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INCOMPLETE)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "plan")


class Wallet(BaseModel):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="wallet")
    balance_cents = models.IntegerField(default=0)


class GiftType(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    price_cents = models.PositiveIntegerField()
    art_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["price_cents"]
