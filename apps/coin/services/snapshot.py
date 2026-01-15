from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.coin.models import CoinLedgerEntry, MonthlyCoinSnapshot


@dataclass
class CoinSnapshotResult:
    period: str
    ledger_hash: str
    total_events: int
    total_entries: int
    total_volume_cents: int
    csv_bytes: bytes
    snapshot: MonthlyCoinSnapshot | None


def parse_period(period: str) -> Tuple[date, date]:
    try:
        year_str, month_str = period.split("-")
        year, month = int(year_str), int(month_str)
        start = date(year, month, 1)
    except Exception as exc:
        raise ValidationError("Period must be in YYYY-MM format.") from exc

    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _hash_ledger_rows(rows: Iterable[Dict[str, object]]) -> str:
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(json.dumps(row, sort_keys=True).encode("utf-8"))
    return hasher.hexdigest()


def _serialize_entries(entries: List[CoinLedgerEntry]) -> Tuple[List[Dict[str, object]], str, bytes]:
    ledger_rows: List[Dict[str, object]] = []
    for entry in entries:
        ledger_rows.append(
            {
                "id": entry.id,
                "event_id": entry.event_id,
                "event_type": entry.event.event_type,
                "account_key": entry.account_key,
                "direction": entry.direction,
                "amount_cents": entry.amount_cents,
                "currency": entry.currency,
                "entry_metadata": entry.metadata,
                "event_metadata": entry.event.metadata,
                "created_at": entry.created_at.isoformat(),
            }
        )

    ledger_hash = _hash_ledger_rows(ledger_rows)

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "event_id",
            "event_type",
            "account_key",
            "direction",
            "amount_cents",
            "currency",
            "entry_metadata",
            "event_metadata",
            "created_at",
        ],
    )
    writer.writeheader()
    for row in ledger_rows:
        writer.writerow(
            {
                **row,
                "entry_metadata": json.dumps(row["entry_metadata"], sort_keys=True),
                "event_metadata": json.dumps(row["event_metadata"], sort_keys=True),
            }
        )
    return ledger_rows, ledger_hash, buffer.getvalue().encode("utf-8")


def generate_monthly_coin_snapshot(
    *,
    period: str,
    ruleset_version: str = "v1",
    dry_run: bool = True,
) -> CoinSnapshotResult:
    start_date, end_date = parse_period(period)
    start_dt = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
    end_dt = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.min.time()))

    entries = list(
        CoinLedgerEntry.objects.select_related("event")
        .filter(created_at__gte=start_dt, created_at__lt=end_dt, event__ruleset_version=ruleset_version)
        .order_by("created_at", "id")
    )

    _, ledger_hash, csv_bytes = _serialize_entries(entries)
    event_ids = {entry.event_id for entry in entries}
    total_volume_cents = sum(entry.amount_cents for entry in entries)

    snapshot_obj: MonthlyCoinSnapshot | None = None
    if not dry_run:
        with transaction.atomic():
            if MonthlyCoinSnapshot.objects.filter(period=period).exists():
                raise ValidationError("Snapshot already exists for this period.")
            snapshot_obj = MonthlyCoinSnapshot.objects.create(
                period=period,
                total_events=len(event_ids),
                total_entries=len(entries),
                total_volume_cents=total_volume_cents,
                ledger_hash=ledger_hash,
            )

    return CoinSnapshotResult(
        period=period,
        ledger_hash=ledger_hash,
        total_events=len(event_ids),
        total_entries=len(entries),
        total_volume_cents=total_volume_cents,
        csv_bytes=csv_bytes,
        snapshot=snapshot_obj,
    )
