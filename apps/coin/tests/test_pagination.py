from __future__ import annotations

import hashlib

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.coin.models import CoinAccount, CoinLedgerEntry
from apps.coin.services.ledger import mint_for_payment
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
def test_coin_ledger_pagination_stable_with_same_timestamp():
    user = User.objects.create_user(email="page@example.com", password="pass1234", handle="page", name="Page User")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )

    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=100, provider_event_id="evt_a"))
    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=200, provider_event_id="evt_b"))
    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=300, provider_event_id="evt_c"))

    entries = list(
        CoinLedgerEntry.objects.filter(account_key=f"user:{user.id}").order_by("id")
    )
    fixed = timezone.now()
    CoinLedgerEntry.objects.filter(id__in=[entry.id for entry in entries]).update(created_at=fixed)

    ordered_ids = list(
        CoinLedgerEntry.objects.filter(account_key=f"user:{user.id}")
        .order_by("created_at", "id")
        .values_list("id", flat=True)
    )

    client = APIClient()
    client.force_authenticate(user=user)

    resp_one = client.get("/api/v1/coin/ledger/", {"limit": 2})
    assert resp_one.status_code == 200
    data_one = resp_one.json()
    ids_one = [row["id"] for row in data_one["results"]]
    cursor = data_one["next_cursor"]
    assert cursor and isinstance(cursor, str)

    resp_two = client.get("/api/v1/coin/ledger/", {"limit": 2, "cursor": cursor})
    assert resp_two.status_code == 200
    data_two = resp_two.json()
    ids_two = [row["id"] for row in data_two["results"]]

    all_ids = ids_one + ids_two
    assert all_ids == ordered_ids[: len(all_ids)]
    assert len(set(all_ids)) == len(all_ids)


@pytest.mark.django_db
def test_legacy_numeric_cursor_maps_to_composite_boundary():
    user = User.objects.create_user(email="legacy@example.com", password="pass1234", handle="legacy", name="Legacy User")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )

    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=100, provider_event_id="evt_l1"))
    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=200, provider_event_id="evt_l2"))
    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=300, provider_event_id="evt_l3"))

    entries = list(
        CoinLedgerEntry.objects.filter(account_key=f"user:{user.id}").order_by("id")
    )
    fixed = timezone.now()
    CoinLedgerEntry.objects.filter(id__in=[entry.id for entry in entries]).update(created_at=fixed)

    ordered_ids = list(
        CoinLedgerEntry.objects.filter(account_key=f"user:{user.id}")
        .order_by("created_at", "id")
        .values_list("id", flat=True)
    )
    legacy_cursor = str(ordered_ids[1])

    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get("/api/v1/coin/ledger/", {"limit": 10, "cursor": legacy_cursor})
    assert resp.status_code == 200
    data = resp.json()
    ids = [row["id"] for row in data["results"]]
    assert ids[0] == ordered_ids[2]


@pytest.mark.django_db
def test_invalid_cursor_returns_400():
    user = User.objects.create_user(email="badcursor@example.com", password="pass1234", handle="badcursor", name="Bad Cursor")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    mint_for_payment(payment_event=_create_payment_event(user=user, amount_cents=100, provider_event_id="evt_bad"))

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/v1/coin/ledger/", {"cursor": "not-a-valid-cursor"})
    assert resp.status_code == 400
