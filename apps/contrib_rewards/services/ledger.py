from __future__ import annotations

from typing import Iterable, List, Sequence

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.contrib_rewards.models import ContributorProfile, LedgerEntry, RewardEvent, LedgerEntryDirection


def _validate_entries(entries: Sequence[dict]) -> None:
    if not entries:
        raise ValidationError("At least one ledger entry is required.")
    totals: dict[str, int] = {}
    for entry in entries:
        direction = entry.get("direction")
        amount = int(entry.get("amount", 0))
        currency = entry.get("currency", "POINTS")
        if direction not in LedgerEntryDirection.values:
            raise ValidationError(f"Invalid direction: {direction}")
        if amount <= 0:
            raise ValidationError("Amounts must be positive integers.")
        signed = amount if direction == LedgerEntryDirection.CREDIT else -amount
        totals[currency] = totals.get(currency, 0) + signed
    unbalanced = {cur: total for cur, total in totals.items() if total != 0}
    if unbalanced:
        raise ValidationError(f"Unbalanced ledger entries for currency: {unbalanced}")


def _points_from_entries(entries: Sequence[dict], contributor: ContributorProfile) -> int:
    account = f"user:{contributor.user_id}"
    points = 0
    for entry in entries:
        if entry.get("account") != account:
            continue
        if entry.get("currency", "POINTS") != "POINTS":
            continue
        amount = int(entry.get("amount", 0))
        direction = entry.get("direction")
        if direction == LedgerEntryDirection.CREDIT:
            points += amount
        elif direction == LedgerEntryDirection.DEBIT:
            points -= amount
    return points


def post_event_and_ledger_entries(
    *,
    event_type: str,
    contributor: ContributorProfile,
    reference: str | None = None,
    metadata: dict | None = None,
    notes: str = "",
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

    if contributor is None:
        raise ValidationError("Contributor is required for reward events.")
    metadata = metadata or {}
    points = _points_from_entries(entry_list, contributor)

    with transaction.atomic():
        event = RewardEvent.objects.create(
            contributor=contributor,
            event_type=event_type,
            points=points,
            reference=reference or "",
            metadata=metadata,
            notes=notes or "",
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
