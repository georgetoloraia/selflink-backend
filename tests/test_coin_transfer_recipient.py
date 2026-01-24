from __future__ import annotations

import hashlib

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.coin.models import CoinAccount
from apps.coin.services.ledger import mint_for_payment
from apps.payments.models import PaymentEvent
from apps.users.models import User


def _mint_slc(user: User, amount_cents: int, provider_event_id: str) -> None:
    event = PaymentEvent.objects.create(
        provider=PaymentEvent.Provider.STRIPE,
        provider_event_id=provider_event_id,
        event_type="checkout.session.completed",
        user=user,
        amount_cents=amount_cents,
        status=PaymentEvent.Status.RECEIVED,
        raw_body_hash=hashlib.sha256(provider_event_id.encode("utf-8")).hexdigest(),
        verified_at=timezone.now(),
    )
    mint_for_payment(payment_event=event)


@pytest.mark.django_db
def test_me_recipient_id_returns_account_key() -> None:
    user = User.objects.create_user(email="me@example.com", password="pass1234", handle="me", name="Me")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/users/me/recipient-id/")
    assert response.status_code == 200
    assert response.data["account_key"] == CoinAccount.user_account_key(user.id)


@pytest.mark.django_db
def test_transfer_by_account_key_succeeds() -> None:
    sender = User.objects.create_user(email="s@example.com", password="pass1234", handle="s", name="Sender")
    receiver = User.objects.create_user(email="r@example.com", password="pass1234", handle="r", name="Receiver")
    _mint_slc(sender, amount_cents=10000, provider_event_id="evt_transfer_1")

    client = APIClient()
    client.force_authenticate(user=sender)
    payload = {"receiver_account_key": CoinAccount.user_account_key(receiver.id), "amount_cents": 500}
    response = client.post("/api/v1/coin/transfer/", data=payload, format="json")

    assert response.status_code == 201
    assert response.data["to_user_id"] == receiver.id


@pytest.mark.django_db
def test_transfer_invalid_account_key_returns_invalid_receiver() -> None:
    sender = User.objects.create_user(email="s2@example.com", password="pass1234", handle="s2", name="Sender Two")
    _mint_slc(sender, amount_cents=10000, provider_event_id="evt_transfer_2")

    client = APIClient()
    client.force_authenticate(user=sender)
    response = client.post(
        "/api/v1/coin/transfer/",
        data={"receiver_account_key": "user:999999", "amount_cents": 500},
        format="json",
    )

    assert response.status_code == 400
    assert response.data.get("code") == "invalid_receiver"


@pytest.mark.django_db
def test_transfer_self_account_key_blocked() -> None:
    sender = User.objects.create_user(email="s3@example.com", password="pass1234", handle="s3", name="Sender Three")
    _mint_slc(sender, amount_cents=10000, provider_event_id="evt_transfer_3")

    client = APIClient()
    client.force_authenticate(user=sender)
    response = client.post(
        "/api/v1/coin/transfer/",
        data={"receiver_account_key": CoinAccount.user_account_key(sender.id), "amount_cents": 500},
        format="json",
    )

    assert response.status_code == 400
    assert response.data.get("code") == "invalid_receiver"
