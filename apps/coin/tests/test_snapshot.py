from __future__ import annotations

import csv
import io

import hashlib

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.coin.models import CoinLedgerEntry, MonthlyCoinSnapshot
from apps.coin.services.ledger import mint_for_payment
from apps.coin.services.snapshot import generate_monthly_coin_snapshot
from apps.payments.models import PaymentEvent
from apps.users.models import User


def _create_payment_event(*, user: User, amount_cents: int, provider_event_id: str) -> PaymentEvent:
    return PaymentEvent.objects.create(
        provider=PaymentEvent.Provider.STRIPE,
        provider_event_id=provider_event_id,
        event_type="checkout.session.completed",
        user=user,
        amount_cents=amount_cents,
        status=PaymentEvent.Status.RECEIVED,
        raw_body_hash=hashlib.sha256(provider_event_id.encode("utf-8")).hexdigest(),
        verified_at=timezone.now(),
    )


@pytest.mark.django_db
def test_snapshot_determinism():
    user = User.objects.create_user(email="snap@example.com", password="pass1234", handle="snap", name="Snap User")
    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=1500, provider_event_id="evt_snap_1"))

    period = timezone.now().strftime("%Y-%m")
    result_one = generate_monthly_coin_snapshot(period=period, dry_run=True)
    result_two = generate_monthly_coin_snapshot(period=period, dry_run=True)

    assert result_one.ledger_hash == result_two.ledger_hash
    assert result_one.csv_bytes == result_two.csv_bytes

    rows = list(csv.DictReader(io.StringIO(result_one.csv_bytes.decode("utf-8"))))
    entry_ids = [int(row["id"]) for row in rows]
    ordered_ids = list(
        CoinLedgerEntry.objects.order_by("created_at", "id").values_list("id", flat=True)
    )
    assert entry_ids == ordered_ids


@pytest.mark.django_db
def test_snapshot_immutability():
    user = User.objects.create_user(email="snap2@example.com", password="pass1234", handle="snap2", name="Snap Two")
    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=2500, provider_event_id="evt_snap_2"))

    period = timezone.now().strftime("%Y-%m")
    result = generate_monthly_coin_snapshot(period=period, dry_run=False)
    snapshot = result.snapshot
    assert snapshot is not None

    with pytest.raises(ValidationError):
        snapshot.save()
    with pytest.raises(ValidationError):
        snapshot.delete()

    assert MonthlyCoinSnapshot.objects.count() == 1
