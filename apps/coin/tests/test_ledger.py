from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.coin.models import CoinAccount, CoinEvent, CoinLedgerEntry, SYSTEM_ACCOUNT_FEES, SYSTEM_ACCOUNT_MINT
from apps.coin.services.ledger import (
    calculate_fee_cents,
    create_transfer,
    mint_for_payment,
    post_event_and_entries,
)
from apps.coin.services.payments import mint_from_payment_event
from apps.users.models import User


@pytest.mark.django_db
def test_balanced_transaction_succeeds():
    user = User.objects.create_user(email="u1@example.com", password="pass1234", handle="u1", name="User One")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )

    event = post_event_and_entries(
        event_type=CoinEvent.EventType.MINT,
        created_by=None,
        entries=[
            {
                "account_key": SYSTEM_ACCOUNT_MINT,
                "amount_cents": 1000,
                "currency": "SLC",
                "direction": CoinLedgerEntry.Direction.DEBIT,
            },
            {
                "account_key": f"user:{user.id}",
                "amount_cents": 1000,
                "currency": "SLC",
                "direction": CoinLedgerEntry.Direction.CREDIT,
            },
        ],
    )
    entries = list(event.ledger_entries.all())
    assert len(entries) == 2
    credits = [e for e in entries if e.direction == CoinLedgerEntry.Direction.CREDIT]
    debits = [e for e in entries if e.direction == CoinLedgerEntry.Direction.DEBIT]
    assert sum(e.amount_cents for e in credits) == sum(e.amount_cents for e in debits)


@pytest.mark.django_db
def test_unbalanced_transaction_raises():
    user = User.objects.create_user(email="u2@example.com", password="pass1234", handle="u2", name="User Two")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    with pytest.raises(ValidationError):
        post_event_and_entries(
            event_type=CoinEvent.EventType.MINT,
            created_by=None,
            entries=[
                {
                    "account_key": SYSTEM_ACCOUNT_MINT,
                    "amount_cents": 500,
                    "currency": "SLC",
                    "direction": CoinLedgerEntry.Direction.DEBIT,
                },
                {
                    "account_key": f"user:{user.id}",
                    "amount_cents": 300,
                    "currency": "SLC",
                    "direction": CoinLedgerEntry.Direction.CREDIT,
                },
            ],
        )
    assert CoinEvent.objects.count() == 0
    assert CoinLedgerEntry.objects.count() == 0


@pytest.mark.django_db
def test_immutability():
    user = User.objects.create_user(email="u3@example.com", password="pass1234", handle="u3", name="User Three")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    event = post_event_and_entries(
        event_type=CoinEvent.EventType.MINT,
        created_by=None,
        entries=[
            {
                "account_key": SYSTEM_ACCOUNT_MINT,
                "amount_cents": 200,
                "currency": "SLC",
                "direction": CoinLedgerEntry.Direction.DEBIT,
            },
            {
                "account_key": f"user:{user.id}",
                "amount_cents": 200,
                "currency": "SLC",
                "direction": CoinLedgerEntry.Direction.CREDIT,
            },
        ],
    )
    with pytest.raises(ValidationError):
        event.save()
    entry = event.ledger_entries.first()
    assert entry is not None
    with pytest.raises(ValidationError):
        entry.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(ValidationError):
        entry.delete()


@pytest.mark.django_db
def test_transfer_applies_fee_and_balances():
    sender = User.objects.create_user(email="u4@example.com", password="pass1234", handle="u4", name="User Four")
    receiver = User.objects.create_user(email="u5@example.com", password="pass1234", handle="u5", name="User Five")
    CoinAccount.objects.get_or_create(
        user=sender,
        defaults={"account_key": CoinAccount.user_account_key(sender.id)},
    )
    CoinAccount.objects.get_or_create(
        user=receiver,
        defaults={"account_key": CoinAccount.user_account_key(receiver.id)},
    )

    mint_for_payment(user=sender, amount_cents=2000, provider="test", external_id="seed")

    amount_cents = 1000
    fee_cents = calculate_fee_cents(amount_cents)
    event = create_transfer(sender=sender, receiver=receiver, amount_cents=amount_cents, fee_cents=fee_cents)

    entries = list(event.ledger_entries.all())
    assert len(entries) == 3
    totals = sum(entry.signed_amount() for entry in entries)
    assert totals == 0

    sender_entry = next(e for e in entries if e.account_key == f"user:{sender.id}")
    receiver_entry = next(e for e in entries if e.account_key == f"user:{receiver.id}")
    fee_entry = next(e for e in entries if e.account_key == SYSTEM_ACCOUNT_FEES)

    assert sender_entry.amount_cents == amount_cents + fee_cents
    assert sender_entry.direction == CoinLedgerEntry.Direction.DEBIT
    assert receiver_entry.amount_cents == amount_cents
    assert receiver_entry.direction == CoinLedgerEntry.Direction.CREDIT
    assert fee_entry.amount_cents == fee_cents
    assert fee_entry.direction == CoinLedgerEntry.Direction.CREDIT


@pytest.mark.django_db
def test_transfer_requires_balance():
    sender = User.objects.create_user(email="u6@example.com", password="pass1234", handle="u6", name="User Six")
    receiver = User.objects.create_user(email="u7@example.com", password="pass1234", handle="u7", name="User Seven")
    CoinAccount.objects.get_or_create(
        user=sender,
        defaults={"account_key": CoinAccount.user_account_key(sender.id)},
    )
    CoinAccount.objects.get_or_create(
        user=receiver,
        defaults={"account_key": CoinAccount.user_account_key(receiver.id)},
    )

    with pytest.raises(ValidationError):
        create_transfer(sender=sender, receiver=receiver, amount_cents=500)


@pytest.mark.django_db
def test_idempotent_mint_for_payment():
    user = User.objects.create_user(email="u8@example.com", password="pass1234", handle="u8", name="User Eight")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    event_one = mint_for_payment(user=user, amount_cents=750, provider="stripe", external_id="evt_1")
    event_two = mint_for_payment(user=user, amount_cents=750, provider="stripe", external_id="evt_1")
    assert event_one.id == event_two.id
    assert CoinEvent.objects.count() == 1
    assert CoinLedgerEntry.objects.count() == 2


@pytest.mark.django_db
def test_idempotent_mint_from_payment_event():
    user = User.objects.create_user(email="u10@example.com", password="pass1234", handle="u10", name="User Ten")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    event_one = mint_from_payment_event(
        user=user,
        amount_cents=500,
        provider="stripe",
        provider_event_id="evt_10",
        metadata={"source": "webhook"},
    )
    event_two = mint_from_payment_event(
        user=user,
        amount_cents=500,
        provider="stripe",
        provider_event_id="evt_10",
        metadata={"source": "webhook"},
    )
    assert event_one.id == event_two.id


@pytest.mark.django_db
@override_settings(COIN_FEE_BPS=250, COIN_FEE_MIN_CENTS=50)
def test_fee_calculation_applies_minimum():
    assert calculate_fee_cents(1000) == 50
    assert calculate_fee_cents(100000) == 2500


@pytest.mark.django_db
def test_unknown_account_key_rejected():
    user = User.objects.create_user(email="u9@example.com", password="pass1234", handle="u9", name="User Nine")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )

    with pytest.raises(ValidationError):
        post_event_and_entries(
            event_type=CoinEvent.EventType.MINT,
            created_by=None,
            entries=[
                {
                    "account_key": SYSTEM_ACCOUNT_MINT,
                    "amount_cents": 100,
                    "currency": "SLC",
                    "direction": CoinLedgerEntry.Direction.DEBIT,
                },
                {
                    "account_key": "user:999999",
                    "amount_cents": 100,
                    "currency": "SLC",
                    "direction": CoinLedgerEntry.Direction.CREDIT,
                },
            ],
        )
