from __future__ import annotations

import hashlib
import uuid

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.coin.models import (
    CoinAccount,
    CoinEvent,
    CoinLedgerEntry,
    SYSTEM_ACCOUNT_FEES,
    SYSTEM_ACCOUNT_MINT,
)
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
def test_invariant_check_happy_path():
    user = User.objects.create_user(email="ok@example.com", password="pass1234", handle="ok", name="Ok")
    payment_event = _create_payment_event(user=user, amount_cents=500, provider_event_id="evt_ok_1")
    mint_for_payment(payment_event=payment_event)

    call_command("coin_invariant_check")


@pytest.mark.django_db
def test_invariant_check_fails_on_missing_payment_event():
    user = User.objects.create_user(email="nopay@example.com", password="pass1234", handle="nopay", name="No Pay")
    event = CoinEvent.objects.create(event_type=CoinEvent.EventType.MINT)
    CoinLedgerEntry.objects.create(
        event=event,
        account_key=SYSTEM_ACCOUNT_MINT,
        amount_cents=100,
        currency="SLC",
        direction=CoinLedgerEntry.Direction.DEBIT,
    )
    CoinLedgerEntry.objects.create(
        event=event,
        account_key=CoinAccount.user_account_key(user.id),
        amount_cents=100,
        currency="SLC",
        direction=CoinLedgerEntry.Direction.CREDIT,
    )
    with pytest.raises(CommandError):
        call_command("coin_invariant_check")


@pytest.mark.django_db
def test_invariant_check_fails_on_unbalanced_tx():
    user = User.objects.create_user(email="unbal@example.com", password="pass1234", handle="unbal", name="Unbal")
    event = CoinEvent.objects.create(event_type=CoinEvent.EventType.TRANSFER)
    tx_id = uuid.uuid4()
    CoinLedgerEntry.objects.create(
        event=event,
        tx_id=tx_id,
        account_key=CoinAccount.user_account_key(user.id),
        amount_cents=250,
        currency="SLC",
        direction=CoinLedgerEntry.Direction.CREDIT,
    )
    with pytest.raises(CommandError):
        call_command("coin_invariant_check")


@pytest.mark.django_db
def test_invariant_check_fails_on_unknown_account():
    event = CoinEvent.objects.create(event_type=CoinEvent.EventType.TRANSFER)
    CoinLedgerEntry.objects.create(
        event=event,
        account_key="user:999999",
        amount_cents=100,
        currency="SLC",
        direction=CoinLedgerEntry.Direction.CREDIT,
    )
    with pytest.raises(CommandError):
        call_command("coin_invariant_check")


@pytest.mark.django_db
def test_invariant_check_fails_on_suspended_user_account():
    user = User.objects.create_user(email="suspend@example.com", password="pass1234", handle="suspend", name="Suspend")
    account = CoinAccount.objects.get(user=user)
    account.status = CoinAccount.Status.SUSPENDED
    account.save(update_fields=["status", "updated_at"])
    event = CoinEvent.objects.create(event_type=CoinEvent.EventType.TRANSFER)
    CoinLedgerEntry.objects.create(
        event=event,
        account_key=account.account_key,
        amount_cents=100,
        currency="SLC",
        direction=CoinLedgerEntry.Direction.CREDIT,
    )
    with pytest.raises(CommandError):
        call_command("coin_invariant_check")


@pytest.mark.django_db
def test_invariant_check_allows_suspended_system_account():
    user = User.objects.create_user(email="sysok@example.com", password="pass1234", handle="sysok", name="Sys Ok")
    system_account = CoinAccount.objects.get(account_key=SYSTEM_ACCOUNT_FEES)
    system_account.status = CoinAccount.Status.SUSPENDED
    system_account.save(update_fields=["status", "updated_at"])
    event = CoinEvent.objects.create(event_type=CoinEvent.EventType.TRANSFER)
    tx_id = uuid.uuid4()
    CoinLedgerEntry.objects.create(
        event=event,
        tx_id=tx_id,
        account_key=system_account.account_key,
        amount_cents=50,
        currency="SLC",
        direction=CoinLedgerEntry.Direction.CREDIT,
    )
    CoinLedgerEntry.objects.create(
        event=event,
        tx_id=tx_id,
        account_key=CoinAccount.user_account_key(user.id),
        amount_cents=50,
        currency="SLC",
        direction=CoinLedgerEntry.Direction.DEBIT,
    )
    call_command("coin_invariant_check")
