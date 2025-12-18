from __future__ import annotations

from typing import Iterable, List, Sequence

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.contrib_rewards.models import LedgerEntry, RewardEvent


def _validate_entries(entries: Sequence[dict]) -> None:
    if not entries:
        raise ValidationError("At least one ledger entry is required.")
    totals: dict[str, int] = {}
    for entry in entries:
        direction = entry.get("direction")
        amount = int(entry.get("amount", 0))
        currency = entry.get("currency", "POINTS")
        if direction not in LedgerEntry.Direction.values:
            raise ValidationError(f"Invalid direction: {direction}")
        if amount <= 0:
            raise ValidationError("Amounts must be positive integers.")
        signed = amount if direction == LedgerEntry.Direction.CREDIT else -amount
        totals[currency] = totals.get(currency, 0) + signed
    unbalanced = {cur: total for cur, total in totals.items() if total != 0}
    if unbalanced:
        raise ValidationError(f"Unbalanced ledger entries for currency: {unbalanced}")


def post_event_and_ledger_entries(
    *,
    event_type: str,
    external_id: str | None = None,
    actor=None,
    payload: dict | None = None,
    ruleset_version: str = "v1",
    entries: Iterable[dict],
) -> RewardEvent:
    """
    Create a RewardEvent and balanced ledger entries atomically.

    entries example:
    {"account": "platform:rewards_pool", "amount": 5, "currency": "POINTS", "direction": "DEBIT"}
    """
    entry_list: List[dict] = list(entries)
    _validate_entries(entry_list)

    # Stable ordering for deterministic hashes downstream.
    entry_list.sort(
        key=lambda e: (
            str(e.get("account", "")),
            str(e.get("direction", "")),
            str(e.get("currency", "")),
            int(e.get("amount", 0)),
        )
    )

    payload = payload or {}

    with transaction.atomic():
        event = RewardEvent.objects.create(
            event_type=event_type,
            external_id=external_id,
            actor=actor,
            payload=payload,
            ruleset_version=ruleset_version,
        )
        rows = [
            LedgerEntry(
                event=event,
                account=entry["account"],
                amount=int(entry["amount"]),
                currency=entry.get("currency", "POINTS"),
                direction=entry["direction"],
            )
            for entry in entry_list
        ]
        LedgerEntry.objects.bulk_create(rows)
    return event
