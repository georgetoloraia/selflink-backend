from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class ContributorProfile(BaseModel):
    """Public contributor identity used for rewards and audits."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contributor_profile",
    )
    github_username = models.CharField(max_length=255, blank=True, null=True, unique=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["github_username"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"Contributor<{self.user_id}>"


class RewardEvent(BaseModel):
    """
    Append-only ledger of contributor reward events.

    Use compensating events instead of updates/deletes.
    """

    class EventType(models.TextChoices):
        PR_MERGED = "pr_merged", "PR merged"
        BOUNTY_PAID = "bounty_paid", "Bounty paid"
        MANUAL_ADJUSTMENT = "manual_adjustment", "Manual adjustment"
        BONUS = "bonus", "Bonus"
        PENALTY = "penalty", "Penalty"

    contributor = models.ForeignKey(
        ContributorProfile,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(max_length=64, choices=EventType.choices)
    points = models.IntegerField(help_text="Positive for rewards, negative for clawbacks.")
    occurred_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="External reference such as PR number or bounty id.",
    )
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["contributor", "occurred_at"]),
            models.Index(fields=["event_type", "occurred_at"]),
        ]

    def save(self, *args, **kwargs) -> None:  # type: ignore[override]
        if self.pk:
            raise ValidationError("RewardEvent rows are immutable. Create a new event instead.")
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        raise ValidationError("RewardEvent rows are immutable. Create offsetting events instead.")

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"RewardEvent<{self.event_type} {self.points}>"


class LedgerEntry(BaseModel):
    class Direction(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    tx_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    event = models.ForeignKey(
        RewardEvent,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    account = models.CharField(max_length=255, db_index=True)
    amount = models.BigIntegerField(help_text="Smallest unit, e.g. integer points.")
    currency = models.CharField(max_length=16, default="POINTS")
    direction = models.CharField(max_length=6, choices=Direction.choices)

    class Meta:
        indexes = [
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["tx_id"]),
        ]
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self._state.adding:
            raise ValidationError("LedgerEntry rows are immutable; create a new entry instead.")
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        raise ValidationError("LedgerEntry rows are immutable; deletion is not allowed.")

    def signed_amount(self) -> int:
        return self.amount if self.direction == self.Direction.CREDIT else -self.amount

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"LedgerEntry<{self.tx_id}:{self.account}:{self.amount}{self.currency}:{self.direction}>"


class MonthlyRewardSnapshot(BaseModel):
    """Monthly snapshot derived from the immutable ledger."""

    period = models.CharField(max_length=7, unique=True, help_text="YYYY-MM")
    revenue_cents = models.PositiveIntegerField(default=0)
    costs_cents = models.PositiveIntegerField(default=0)
    contributor_pool_cents = models.PositiveIntegerField(default=0)
    total_points = models.IntegerField(default=0)
    total_events = models.PositiveIntegerField(default=0)
    ledger_hash = models.CharField(max_length=128, help_text="SHA256 hash of ordered ledger for auditing.")
    dispute_window_ends_at = models.DateTimeField()

    class Meta:
        ordering = ["-period"]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"RewardSnapshot<{self.period}>"


class Payout(BaseModel):
    """Calculated payout per contributor for a given monthly snapshot."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PAID = "paid", "Paid"
        CANCELED = "canceled", "Canceled"

    snapshot = models.ForeignKey(
        MonthlyRewardSnapshot,
        on_delete=models.CASCADE,
        related_name="payouts",
    )
    contributor = models.ForeignKey(
        ContributorProfile,
        on_delete=models.CASCADE,
        related_name="payouts",
    )
    points = models.IntegerField()
    amount_cents = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("snapshot", "contributor")
        indexes = [
            models.Index(fields=["snapshot", "status"]),
            models.Index(fields=["contributor", "status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"Payout<{self.snapshot_id}:{self.contributor_id}:{self.amount_cents}>"
