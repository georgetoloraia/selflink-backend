from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.coin.models import CoinAccount, CoinEvent, CoinLedgerEntry, PaidProduct, UserEntitlement
from apps.coin.services.ledger import post_event_and_entries
from apps.users.models import User


def _seed_balance(user: User, amount_cents: int) -> None:
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    post_event_and_entries(
        event_type=CoinEvent.EventType.TRANSFER,
        created_by=None,
        metadata={"seed": True},
        entries=[
            {
                "account_key": "system:mint",
                "amount_cents": amount_cents,
                "currency": "SLC",
                "direction": CoinLedgerEntry.Direction.DEBIT,
            },
            {
                "account_key": f"user:{user.id}",
                "amount_cents": amount_cents,
                "currency": "SLC",
                "direction": CoinLedgerEntry.Direction.CREDIT,
            },
        ],
    )


@pytest.mark.django_db
def test_products_list_returns_seeded_products():
    user = User.objects.create_user(email="p1@example.com", password="pass1234", handle="p1", name="Prod One")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/v1/coin/products/")
    assert resp.status_code == 200
    payload = resp.json()
    codes = {item.get("code") for item in payload}
    assert "premium_month" in codes
    assert "premium_plus_month" in codes


@pytest.mark.django_db
def test_purchase_idempotent_and_extends_entitlement():
    user = User.objects.create_user(email="p2@example.com", password="pass1234", handle="p2", name="Buyer One")
    _seed_balance(user, 5000)
    product = PaidProduct.objects.get(code="premium_month")

    client = APIClient()
    client.force_authenticate(user=user)
    payload = {
        "product_code": product.code,
        "quantity": 1,
        "idempotency_key": "idem-123",
    }

    resp = client.post("/api/v1/coin/purchase/", payload, format="json")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    entitlements = data.get("entitlements", {})
    assert entitlements.get("premium", {}).get("active") is True

    entitlement = UserEntitlement.objects.get(user=user, key="premium")
    first_until = entitlement.active_until
    assert first_until is not None

    resp2 = client.post("/api/v1/coin/purchase/", payload, format="json")
    assert resp2.status_code == 200
    entitlement.refresh_from_db()
    assert entitlement.active_until == first_until


@pytest.mark.django_db
def test_premium_plus_implies_premium():
    user = User.objects.create_user(email="p3@example.com", password="pass1234", handle="p3", name="Buyer Two")
    _seed_balance(user, 5000)
    product = PaidProduct.objects.get(code="premium_plus_month")

    client = APIClient()
    client.force_authenticate(user=user)
    payload = {
        "product_code": product.code,
        "quantity": 1,
        "idempotency_key": "idem-456",
    }

    resp = client.post("/api/v1/coin/purchase/", payload, format="json")
    assert resp.status_code == 200
    entitlements = resp.json().get("entitlements", {})
    assert entitlements.get("premium_plus", {}).get("active") is True
    assert entitlements.get("premium", {}).get("active") is True

    premium = UserEntitlement.objects.get(user=user, key="premium")
    premium_plus = UserEntitlement.objects.get(user=user, key="premium_plus")
    assert premium.active_until is not None
    assert premium_plus.active_until is not None
    assert premium.active_until >= premium_plus.active_until


@pytest.mark.django_db
def test_purchase_insufficient_balance():
    user = User.objects.create_user(email="p4@example.com", password="pass1234", handle="p4", name="Buyer Three")
    _seed_balance(user, 50)
    product = PaidProduct.objects.get(code="premium_month")

    client = APIClient()
    client.force_authenticate(user=user)
    payload = {
        "product_code": product.code,
        "quantity": 1,
        "idempotency_key": "idem-789",
    }

    resp = client.post("/api/v1/coin/purchase/", payload, format="json")
    assert resp.status_code == 402
    data = resp.json()
    assert data.get("code") == "insufficient_funds"
