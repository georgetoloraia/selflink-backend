from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel

COIN_CURRENCY = "SLC"
USER_ACCOUNT_PREFIX = "user:"
SYSTEM_ACCOUNT_FEES = "system:fees"
SYSTEM_ACCOUNT_REVENUE = "system:revenue"
SYSTEM_ACCOUNT_MINT = "system:mint"
# Only these system accounts are allowed in ledger postings.
SYSTEM_ACCOUNT_KEYS = {
    SYSTEM_ACCOUNT_FEES,
    SYSTEM_ACCOUNT_REVENUE,
    SYSTEM_ACCOUNT_MINT,
}


class CoinAccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class CoinEventType(models.TextChoices):
    MINT = "mint", "Mint"
    TRANSFER = "transfer", "Transfer"
    SPEND = "spend", "Spend"
    REFUND = "refund", "Refund"


class CoinLedgerEntryDirection(models.TextChoices):
    DEBIT = "DEBIT", "Debit"
    CREDIT = "CREDIT", "Credit"


class CoinAccount(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coin_account",
        null=True,
        blank=True,
    )
    account_key = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255, blank=True)
    is_system = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=CoinAccountStatus.choices, default=CoinAccountStatus.ACTIVE)

    class Meta:
        indexes = [
            models.Index(fields=["account_key"]),
        ]

    @staticmethod
    def user_account_key(user_id: int) -> str:
        return f"{USER_ACCOUNT_PREFIX}{user_id}"

    def clean(self) -> None:
        if self.user_id and not self.account_key.startswith(USER_ACCOUNT_PREFIX):
            raise ValidationError("User coin accounts must use the user:<id> account_key format.")
        if self.is_system and self.user_id:
            raise ValidationError("System coin accounts cannot be linked to a user.")

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return self.account_key


class CoinEvent(BaseModel):
    event_type = models.CharField(max_length=32, choices=CoinEventType.choices)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="coin_events",
        null=True,
        blank=True,
    )
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=255, blank=True)
    ruleset_version = models.CharField(max_length=16, default="v1")

    class Meta:
        ordering = ["-occurred_at", "-created_at"]

    def save(self, *args, **kwargs) -> None:  # type: ignore[override]
        if not self._state.adding:
            raise ValidationError("CoinEvent rows are immutable. Create a new event instead.")
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        raise ValidationError("CoinEvent rows are immutable; deletion is not allowed.")


class CoinLedgerEntry(BaseModel):
    tx_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    event = models.ForeignKey(
        CoinEvent,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    account_key = models.CharField(max_length=255)
    amount_cents = models.BigIntegerField(help_text="Smallest unit in cents.")
    currency = models.CharField(max_length=16, default=COIN_CURRENCY)
    direction = models.CharField(max_length=6, choices=CoinLedgerEntryDirection.choices)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["account_key", "created_at"]),
        ]
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(check=models.Q(amount_cents__gt=0), name="coin_amount_cents_gt_0"),
        ]

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self._state.adding:
            raise ValidationError("CoinLedgerEntry rows are immutable; create a new entry instead.")
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        raise ValidationError("CoinLedgerEntry rows are immutable; deletion is not allowed.")

    def signed_amount(self) -> int:
        return self.amount_cents if self.direction == CoinLedgerEntryDirection.CREDIT else -self.amount_cents


class MonthlyCoinSnapshot(BaseModel):
    period = models.CharField(max_length=7, unique=True, help_text="YYYY-MM")
    total_events = models.PositiveIntegerField(default=0)
    total_entries = models.PositiveIntegerField(default=0)
    total_volume_cents = models.BigIntegerField(default=0)
    ledger_hash = models.CharField(max_length=128, help_text="SHA256 hash of ordered ledger for auditing.")

    class Meta:
        ordering = ["-period"]

    def save(self, *args, **kwargs) -> None:  # type: ignore[override]
        if not self._state.adding:
            raise ValidationError("MonthlyCoinSnapshot rows are immutable. Create a new snapshot instead.")
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        raise ValidationError("MonthlyCoinSnapshot rows are immutable; deletion is not allowed.")


class EntitlementKey(models.TextChoices):
    PREMIUM = "premium", "Premium"
    PREMIUM_PLUS = "premium_plus", "Premium Plus"


class PaidProduct(BaseModel):
    code = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    price_slc = models.BigIntegerField(help_text="SLC cents; integer smallest unit.")
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    entitlement_key = models.CharField(max_length=32, choices=EntitlementKey.choices)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price_slc"]


class UserEntitlement(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="entitlements",
    )
    key = models.CharField(max_length=32, choices=EntitlementKey.choices)
    active_until = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=32, default="slc")
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "key")
        indexes = [
            models.Index(fields=["user", "key"]),
        ]

    @property
    def is_active(self) -> bool:
        if not self.active_until:
            return False
        return self.active_until > timezone.now()
