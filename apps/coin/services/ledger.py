from __future__ import annotations

from typing import Iterable, List, Sequence

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Case, F, Sum, When

from apps.coin.models import (
    COIN_CURRENCY,
    SYSTEM_ACCOUNT_FEES,
    SYSTEM_ACCOUNT_KEYS,
    SYSTEM_ACCOUNT_MINT,
    SYSTEM_ACCOUNT_REVENUE,
    CoinAccount,
    CoinEvent,
    CoinLedgerEntry,
)
from apps.payments.models import PaymentEvent
from apps.users.models import User


def calculate_fee_cents(amount_cents: int) -> int:
    if amount_cents <= 0:
        return 0
    bps = int(getattr(settings, "COIN_FEE_BPS", 100))
    minimum = int(getattr(settings, "COIN_FEE_MIN_CENTS", 25))
    fee = (amount_cents * bps) // 10000
    if fee < minimum:
        fee = minimum
    return max(fee, 0)


def _validate_entries(entries: Sequence[dict]) -> None:
    if not entries:
        raise ValidationError("At least one ledger entry is required.")
    totals: dict[str, int] = {}
    account_keys: set[str] = set()
    for entry in entries:
        account_key = entry.get("account_key")
        if not account_key:
            raise ValidationError("account_key is required for ledger entries.")
        account_keys.add(account_key)
        direction = entry.get("direction")
        amount = int(entry.get("amount_cents", 0))
        currency = entry.get("currency", COIN_CURRENCY)
        if currency != COIN_CURRENCY:
            raise ValidationError(f"Unsupported currency: {currency}")
        if direction not in CoinLedgerEntry.Direction.values:
            raise ValidationError(f"Invalid direction: {direction}")
        if amount <= 0:
            raise ValidationError("Amounts must be positive integers.")
        signed = amount if direction == CoinLedgerEntry.Direction.CREDIT else -amount
        totals[currency] = totals.get(currency, 0) + signed
    unbalanced = {cur: total for cur, total in totals.items() if total != 0}
    if unbalanced:
        raise ValidationError(f"Unbalanced ledger entries for currency: {unbalanced}")
    if account_keys:
        invalid_system_keys = sorted(
            key for key in account_keys if key.startswith("system:") and key not in SYSTEM_ACCOUNT_KEYS
        )
        if invalid_system_keys:
            raise ValidationError("System account is not allowed.")
        accounts = list(
            CoinAccount.objects.filter(account_key__in=account_keys).values("account_key", "status", "is_system")
        )
        existing = {account["account_key"] for account in accounts}
        missing = sorted(account_keys - existing)
        if missing:
            raise ValidationError(f"Unknown account_key(s): {', '.join(missing)}")
        inactive = sorted(
            account["account_key"]
            for account in accounts
            if account["status"] != CoinAccount.Status.ACTIVE
        )
        if inactive:
            raise ValidationError("Coin account is not active.")
        disallowed = sorted(
            account["account_key"]
            for account in accounts
            if account["is_system"] and account["account_key"] not in SYSTEM_ACCOUNT_KEYS
        )
        if disallowed:
            raise ValidationError("System account is not allowed.")


def get_or_create_user_account(user: User) -> CoinAccount:
    account_key = CoinAccount.user_account_key(user.id)
    account, _ = CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": account_key},
    )
    if account.is_system:
        raise ValidationError("User coin accounts cannot be system accounts.")
    if account.account_key != account_key:
        raise ValidationError("Coin account key mismatch for user.")
    if account.status != CoinAccount.Status.ACTIVE:
        raise ValidationError("Coin account is not active.")
    return account


def get_balance_cents(account_key: str) -> int:
    total = CoinLedgerEntry.objects.filter(account_key=account_key).aggregate(
        total=Sum(
            Case(
                When(direction=CoinLedgerEntry.Direction.CREDIT, then=F("amount_cents")),
                When(direction=CoinLedgerEntry.Direction.DEBIT, then=-F("amount_cents")),
                default=0,
                output_field=models.BigIntegerField(),
            )
        )
    )["total"]
    return int(total or 0)


def post_event_and_entries(
    *,
    event_type: str,
    entries: Iterable[dict],
    created_by: User | None = None,
    metadata: dict | None = None,
    note: str = "",
    idempotency_key: str | None = None,
    ruleset_version: str = "v1",
) -> CoinEvent:
    if event_type == CoinEvent.EventType.MINT:
        if not idempotency_key or ":" not in idempotency_key:
            raise ValidationError("Mint events require a provider:event_id idempotency_key.")
        provider, external_id = idempotency_key.split(":", 1)
        payment_event = PaymentEvent.objects.filter(
            provider=provider,
            provider_event_id=external_id,
        ).only("id", "status", "verified_at").first()
        if not payment_event:
            raise ValidationError("PaymentEvent not found for mint.")
        if payment_event.status == PaymentEvent.Status.FAILED:
            raise ValidationError("PaymentEvent is failed.")
        if not payment_event.verified_at:
            raise ValidationError("PaymentEvent is unverified.")
    entry_list: List[dict] = list(entries)
    _validate_entries(entry_list)

    entry_list.sort(
        key=lambda e: (
            str(e.get("account_key", "")),
            str(e.get("direction", "")),
            str(e.get("currency", "")),
            int(e.get("amount_cents", 0)),
        )
    )

    metadata = metadata or {}

    with transaction.atomic():
        event = CoinEvent.objects.create(
            event_type=event_type,
            created_by=created_by,
            metadata=metadata,
            note=note or "",
            idempotency_key=idempotency_key,
            ruleset_version=ruleset_version,
        )
        rows = [
            CoinLedgerEntry(
                event=event,
                account_key=entry["account_key"],
                amount_cents=int(entry["amount_cents"]),
                currency=entry.get("currency", COIN_CURRENCY),
                direction=entry["direction"],
                metadata=entry.get("metadata", {}),
            )
            for entry in entry_list
        ]
        CoinLedgerEntry.objects.bulk_create(rows)
    return event


def create_transfer(
    *,
    sender: User,
    receiver: User,
    amount_cents: int,
    fee_cents: int | None = None,
    note: str = "",
) -> CoinEvent:
    if sender.id == receiver.id:
        raise ValidationError("Cannot transfer to the same user.")
    if amount_cents <= 0:
        raise ValidationError("Amount must be positive.")
    fee = fee_cents if fee_cents is not None else calculate_fee_cents(amount_cents)
    if fee < 0:
        raise ValidationError("Fee must be non-negative.")
    if amount_cents <= fee:
        raise ValidationError("Amount must be greater than the transfer fee.")

    sender_account = get_or_create_user_account(sender)
    receiver_account = get_or_create_user_account(receiver)
    total_debit = amount_cents + fee

    with transaction.atomic():
        CoinAccount.objects.select_for_update().filter(id=sender_account.id).get()
        balance = get_balance_cents(sender_account.account_key)
        if balance < total_debit:
            raise ValidationError("insufficient_funds")
        event = post_event_and_entries(
            event_type=CoinEvent.EventType.TRANSFER,
            created_by=sender,
            note=note,
            metadata={
                "sender_user_id": sender.id,
                "to_user_id": receiver.id,
                "amount_cents": amount_cents,
                "fee_cents": fee,
            },
            entries=[
                {
                    "account_key": sender_account.account_key,
                    "amount_cents": total_debit,
                    "currency": COIN_CURRENCY,
                    "direction": CoinLedgerEntry.Direction.DEBIT,
                },
                {
                    "account_key": receiver_account.account_key,
                    "amount_cents": amount_cents,
                    "currency": COIN_CURRENCY,
                    "direction": CoinLedgerEntry.Direction.CREDIT,
                },
                {
                    "account_key": SYSTEM_ACCOUNT_FEES,
                    "amount_cents": fee,
                    "currency": COIN_CURRENCY,
                    "direction": CoinLedgerEntry.Direction.CREDIT,
                },
            ],
        )
    return event


def create_spend(*, user: User, amount_cents: int, reference: str, note: str = "") -> CoinEvent:
    if amount_cents <= 0:
        raise ValidationError("Amount must be positive.")
    account = get_or_create_user_account(user)

    with transaction.atomic():
        CoinAccount.objects.select_for_update().filter(id=account.id).get()
        balance = get_balance_cents(account.account_key)
        if balance < amount_cents:
            raise ValidationError("insufficient_funds")
        event = post_event_and_entries(
            event_type=CoinEvent.EventType.SPEND,
            created_by=user,
            note=note,
            metadata={
                "user_id": user.id,
                "reference": reference,
                "amount_cents": amount_cents,
            },
            entries=[
                {
                    "account_key": account.account_key,
                    "amount_cents": amount_cents,
                    "currency": COIN_CURRENCY,
                    "direction": CoinLedgerEntry.Direction.DEBIT,
                },
                {
                    "account_key": SYSTEM_ACCOUNT_REVENUE,
                    "amount_cents": amount_cents,
                    "currency": COIN_CURRENCY,
                    "direction": CoinLedgerEntry.Direction.CREDIT,
                },
            ],
        )
    return event


def mint_for_payment(*, payment_event: PaymentEvent, metadata: dict | None = None) -> CoinEvent:
    if payment_event is None or payment_event.pk is None:
        raise ValidationError("PaymentEvent is required.")
    if payment_event.status == PaymentEvent.Status.FAILED:
        raise ValidationError("PaymentEvent is failed.")
    if not payment_event.verified_at:
        raise ValidationError("PaymentEvent is unverified.")
    if payment_event.amount_cents <= 0:
        raise ValidationError("Amount must be positive.")
    if payment_event.minted_coin_event_id:
        if payment_event.status != PaymentEvent.Status.MINTED:
            payment_event.status = PaymentEvent.Status.MINTED
            payment_event.save(update_fields=["status", "updated_at"])
        return payment_event.minted_coin_event  # type: ignore[return-value]
    idempotency_key = f"{payment_event.provider}:{payment_event.provider_event_id}"
    existing = CoinEvent.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if payment_event.minted_coin_event_id is None:
            payment_event.minted_coin_event = existing
            payment_event.status = PaymentEvent.Status.MINTED
            payment_event.save(update_fields=["minted_coin_event", "status", "updated_at"])
        return existing
    account = get_or_create_user_account(payment_event.user)
    event_metadata = metadata or {}
    event_metadata.update(
        {
            "provider": payment_event.provider,
            "external_id": payment_event.provider_event_id,
            "amount_cents": payment_event.amount_cents,
        }
    )
    try:
        with transaction.atomic():
            event = post_event_and_entries(
                event_type=CoinEvent.EventType.MINT,
                created_by=None,
                metadata=event_metadata,
                idempotency_key=idempotency_key,
                entries=[
                    {
                        "account_key": SYSTEM_ACCOUNT_MINT,
                        "amount_cents": payment_event.amount_cents,
                        "currency": COIN_CURRENCY,
                        "direction": CoinLedgerEntry.Direction.DEBIT,
                    },
                    {
                        "account_key": account.account_key,
                        "amount_cents": payment_event.amount_cents,
                        "currency": COIN_CURRENCY,
                        "direction": CoinLedgerEntry.Direction.CREDIT,
                    },
                ],
            )
            payment_event.minted_coin_event = event
            payment_event.status = PaymentEvent.Status.MINTED
            payment_event.save(update_fields=["minted_coin_event", "status", "updated_at"])
            return event
    except IntegrityError:
        existing = CoinEvent.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if payment_event.minted_coin_event_id is None:
                payment_event.minted_coin_event = existing
                payment_event.status = PaymentEvent.Status.MINTED
                payment_event.save(update_fields=["minted_coin_event", "status", "updated_at"])
            return existing
        raise
