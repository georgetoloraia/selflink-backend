from __future__ import annotations

import csv
import hashlib
import io
from datetime import date

from django.db.models import QuerySet
from django.utils import timezone

from apps.contrib_rewards.models import LedgerEntry, LedgerEntryDirection


def _month_bounds(month: str) -> tuple[date, date]:
    try:
        year_str, month_str = month.split("-")
        year, mon = int(year_str), int(month_str)
        start = date(year, mon, 1)
    except Exception as exc:  # pragma: no cover - guardrail
        raise ValueError("Month must be in YYYY-MM format") from exc
    if mon == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, mon + 1, 1)
    return start, end


def _hash_lines(lines: list[str]) -> str:
    sha = hashlib.sha256()
    for line in lines:
        sha.update(line.encode("utf-8"))
    return sha.hexdigest()


def _ledger_queryset(start_dt, end_dt) -> QuerySet[LedgerEntry]:
    return (
        LedgerEntry.objects.select_related("event")
        .filter(created_at__gte=start_dt, created_at__lt=end_dt)
        .order_by("created_at", "id")
    )


def generate_monthly_payout(month: str, ruleset_version: str = "v1", dry_run: bool = True):
    """
    Deterministically compute monthly payout CSV and hashes.

    Returns (csv_text, inputs_hash, outputs_hash, summary_dict)
    """
    start_date, end_date = _month_bounds(month)
    start_dt = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
    end_dt = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.min.time()))

    qs = _ledger_queryset(start_dt, end_dt).filter(event__ruleset_version=ruleset_version)

    input_lines: list[str] = []
    for entry in qs:
        created_iso = entry.created_at.isoformat()
        line = "|".join(
            [
                str(entry.tx_id),
                str(entry.event_id),
                entry.account,
                entry.direction,
                str(entry.amount),
                entry.currency,
                created_iso,
            ]
        )
        input_lines.append(line)
    inputs_hash = _hash_lines(input_lines)

    balances: dict[int, int] = {}
    for entry in qs:
        if not entry.account.startswith("user:"):
            continue
        if entry.currency != "POINTS":
            continue
        try:
            user_id = int(entry.account.split("user:")[1])
        except Exception:
            continue
        delta = entry.amount if entry.direction == LedgerEntryDirection.CREDIT else -entry.amount
        balances[user_id] = balances.get(user_id, 0) + delta

    rows = [(user_id, points) for user_id, points in balances.items() if points != 0]
    rows.sort(key=lambda item: (-item[1], item[0]))

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["user_id", "points"])
    for user_id, points in rows:
        writer.writerow([user_id, points])

    csv_text = buffer.getvalue()
    outputs_hash = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()

    summary = {
        "month": month,
        "ruleset_version": ruleset_version,
        "user_count": len(rows),
        "total_points": sum(points for _, points in rows),
        "inputs_hash": inputs_hash,
        "outputs_hash": outputs_hash,
    }
    return csv_text, inputs_hash, outputs_hash, summary
