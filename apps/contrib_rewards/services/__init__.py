from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.contrib_rewards.models import ContributorProfile, MonthlyRewardSnapshot, Payout, RewardEvent, PayoutStatus


@dataclass
class PayoutLine:
    contributor: ContributorProfile
    points: int
    amount_cents: int


@dataclass
class RewardComputation:
    period: str
    ledger_hash: str
    revenue_cents: int
    costs_cents: int
    contributor_pool_cents: int
    total_points: int
    total_events: int
    payouts: List[PayoutLine]
    csv_bytes: bytes
    snapshot: MonthlyRewardSnapshot | None


def parse_period(period: str) -> Tuple[date, date]:
    """
    Convert "YYYY-MM" to date bounds (inclusive start, exclusive end of next month).
    """
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


def _serialize_events_for_audit(events: List[RewardEvent]) -> Tuple[List[Dict[str, object]], str, bytes]:
    ledger_rows: List[Dict[str, object]] = []
    for event in events:
        ledger_rows.append(
            {
                "id": event.id,
                "contributor_id": event.contributor_id,
                "event_type": event.event_type,
                "points": event.points,
                "occurred_at": event.occurred_at.isoformat(),
                "reference": event.reference,
                "metadata": event.metadata,
            }
        )

    ledger_hash = _hash_ledger_rows(ledger_rows)

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["id", "contributor_id", "event_type", "points", "occurred_at", "reference", "metadata"],
    )
    writer.writeheader()
    for row in ledger_rows:
        writer.writerow({**row, "metadata": json.dumps(row["metadata"], sort_keys=True)})
    return ledger_rows, ledger_hash, buffer.getvalue().encode("utf-8")


def _allocate_pool(contributor_points: Dict[int, int], pool_cents: int) -> Dict[int, int]:
    """
    Deterministically distribute pool_cents proportionally to contributor_points.
    Uses integer math and largest-remainder to keep totals consistent.
    """
    if pool_cents <= 0 or not contributor_points:
        return {}

    total_points = sum(contributor_points.values())
    if total_points <= 0:
        return {}

    base_allocations: Dict[int, int] = {}
    remainders: List[Tuple[int, int]] = []

    for contributor_id, points in contributor_points.items():
        share = pool_cents * points / total_points
        cents = int(share)
        base_allocations[contributor_id] = cents
        remainder = int(round((share - cents) * 1000000))
        remainders.append((contributor_id, remainder))

    distributed = sum(base_allocations.values())
    remainder_cents = pool_cents - distributed
    if remainder_cents <= 0:
        return base_allocations

    # give leftover cents to contributors with the largest remainder, stable-sorted by contributor id
    for contributor_id, _ in sorted(remainders, key=lambda item: (-item[1], item[0]))[: remainder_cents]:
        base_allocations[contributor_id] += 1

    return base_allocations


def calculate_monthly_rewards(
    period: str,
    revenue_cents: int,
    costs_cents: int,
    pool_percent: int = 50,
    dispute_window_days: int = 7,
    dry_run: bool = False,
) -> RewardComputation:
    start_date, end_date = parse_period(period)
    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end_date, datetime.min.time()))

    events = list(
        RewardEvent.objects.select_related("contributor", "contributor__user")
        .filter(occurred_at__gte=start_dt, occurred_at__lt=end_dt)
        .order_by("occurred_at", "id")
    )
    contributor_points: Dict[int, int] = {}
    for event in events:
        contributor_points[event.contributor_id] = contributor_points.get(event.contributor_id, 0) + event.points

    ledger_rows, ledger_hash, csv_bytes = _serialize_events_for_audit(events)
    total_points = sum(contributor_points.values())
    total_events = len(events)

    net_revenue = max(revenue_cents - costs_cents, 0)
    contributor_pool_cents = int(net_revenue * (pool_percent / 100))

    allocations = _allocate_pool(contributor_points, contributor_pool_cents)
    payouts: List[PayoutLine] = []
    contributors_by_id = {event.contributor_id: event.contributor for event in events}
    for contributor_id, points in contributor_points.items():
        contributor = contributors_by_id.get(contributor_id) or ContributorProfile.objects.get(id=contributor_id)
        payouts.append(
            PayoutLine(
                contributor=contributor,
                points=points,
                amount_cents=allocations.get(contributor_id, 0),
            )
        )

    snapshot_obj: MonthlyRewardSnapshot | None = None
    if not dry_run:
        if MonthlyRewardSnapshot.objects.filter(period=period).exists():
            raise ValidationError(f"Snapshot for period {period} already exists. Use a new period or rollback explicitly.")

        dispute_window_end = timezone.make_aware(datetime.combine(end_date, datetime.min.time())) + timedelta(days=dispute_window_days)
        with transaction.atomic():
            snapshot_obj = MonthlyRewardSnapshot.objects.create(
                period=period,
                revenue_cents=revenue_cents,
                costs_cents=costs_cents,
                contributor_pool_cents=contributor_pool_cents,
                total_points=total_points,
                total_events=total_events,
                ledger_hash=ledger_hash,
                dispute_window_ends_at=dispute_window_end,
            )
            payout_models = [
                Payout(
                    snapshot=snapshot_obj,
                    contributor=payout.contributor,
                    points=payout.points,
                    amount_cents=payout.amount_cents,
                    status=PayoutStatus.PENDING,
                )
                for payout in payouts
            ]
            if payout_models:
                Payout.objects.bulk_create(payout_models)

    return RewardComputation(
        period=period,
        ledger_hash=ledger_hash,
        revenue_cents=revenue_cents,
        costs_cents=costs_cents,
        contributor_pool_cents=contributor_pool_cents,
        total_points=total_points,
        total_events=total_events,
        payouts=payouts,
        csv_bytes=csv_bytes,
        snapshot=snapshot_obj,
    )
