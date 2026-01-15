from __future__ import annotations

import hashlib

import pytest
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import override_settings
from django.utils import timezone

from apps.coin.models import (
    CoinAccount,
    CoinEvent,
    CoinLedgerEntry,
    SYSTEM_ACCOUNT_FEES,
    SYSTEM_ACCOUNT_MINT,
    SYSTEM_ACCOUNT_REVENUE,
)
from apps.coin.services.ledger import (
    calculate_fee_cents,
    create_spend,
    create_transfer,
    mint_for_payment,
    post_event_and_entries,
)
from apps.coin.services.payments import mint_from_payment_event
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
def test_balanced_transaction_succeeds():
    user = User.objects.create_user(email="u1@example.com", password="pass1234", handle="u1", name="User One")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )

    event = post_event_and_entries(
        event_type=CoinEvent.EventType.TRANSFER,
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
            event_type=CoinEvent.EventType.TRANSFER,
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
        event_type=CoinEvent.EventType.TRANSFER,
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

    payment_event = _create_payment_event(user=sender, amount_cents=2000, provider_event_id="seed")
    mint_for_payment(payment_event=payment_event)

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
    payment_event = _create_payment_event(user=user, amount_cents=750, provider_event_id="evt_1")
    event_one = mint_for_payment(payment_event=payment_event)
    event_two = mint_for_payment(payment_event=payment_event)
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
    payment_event = _create_payment_event(user=user, amount_cents=500, provider_event_id="evt_10")
    event_one = mint_from_payment_event(payment_event=payment_event, metadata={"source": "webhook"})
    event_two = mint_from_payment_event(payment_event=payment_event, metadata={"source": "webhook"})
    assert event_one.id == event_two.id


@pytest.mark.django_db
def test_mint_requires_payment_event():
    with pytest.raises(ValidationError):
        mint_from_payment_event(payment_event_id=999999)


@pytest.mark.django_db
def test_unverified_payment_event_blocks_mint():
    user = User.objects.create_user(
        email="u_unverified@example.com",
        password="pass1234",
        handle="u_unverified",
        name="User Unverified",
    )
    payment_event = PaymentEvent.objects.create(
        provider=PaymentEvent.Provider.STRIPE,
        provider_event_id="evt_unverified",
        event_type="checkout.session.completed",
        user=user,
        amount_cents=1000,
        status=PaymentEvent.Status.RECEIVED,
        raw_body_hash="hash",
        verified_at=None,
    )
    with pytest.raises(ValidationError):
        mint_for_payment(payment_event=payment_event)


@pytest.mark.django_db
@override_settings(COIN_FEE_BPS=250, COIN_FEE_MIN_CENTS=50)
def test_fee_calculation_applies_minimum():
    assert calculate_fee_cents(1000) == 50
    assert calculate_fee_cents(100000) == 2500


@pytest.mark.django_db
def test_spend_posts_to_revenue_account():
    user = User.objects.create_user(email="spend@example.com", password="pass1234", handle="spend", name="Spend User")
    payment_event = _create_payment_event(user=user, amount_cents=1200, provider_event_id="evt_spend_1")
    mint_for_payment(payment_event=payment_event)

    event = create_spend(user=user, amount_cents=200, reference="product:test")
    entries = list(event.ledger_entries.all())
    revenue_entry = next(e for e in entries if e.account_key == SYSTEM_ACCOUNT_REVENUE)
    assert revenue_entry.direction == CoinLedgerEntry.Direction.CREDIT
    assert revenue_entry.amount_cents == 200


@pytest.mark.django_db
def test_suspended_accounts_cannot_send_or_receive():
    sender = User.objects.create_user(email="u11@example.com", password="pass1234", handle="u11", name="User Eleven")
    receiver = User.objects.create_user(
        email="u12@example.com", password="pass1234", handle="u12", name="User Twelve"
    )
    payment_event = _create_payment_event(user=sender, amount_cents=1000, provider_event_id="evt_suspend_1")
    mint_for_payment(payment_event=payment_event)

    sender_account = CoinAccount.objects.get(user=sender)
    sender_account.status = CoinAccount.Status.SUSPENDED
    sender_account.save(update_fields=["status", "updated_at"])

    with pytest.raises(ValidationError):
        create_transfer(sender=sender, receiver=receiver, amount_cents=200)

    sender_account.status = CoinAccount.Status.ACTIVE
    sender_account.save(update_fields=["status", "updated_at"])

    receiver_account = CoinAccount.objects.get(user=receiver)
    receiver_account.status = CoinAccount.Status.SUSPENDED
    receiver_account.save(update_fields=["status", "updated_at"])

    with pytest.raises(ValidationError):
        create_transfer(sender=sender, receiver=receiver, amount_cents=200)


@pytest.mark.django_db
def test_suspended_system_account_rejected():
    sender = User.objects.create_user(email="u13@example.com", password="pass1234", handle="u13", name="User Thirteen")
    receiver = User.objects.create_user(
        email="u14@example.com", password="pass1234", handle="u14", name="User Fourteen"
    )
    payment_event = _create_payment_event(user=sender, amount_cents=1000, provider_event_id="evt_suspend_2")
    mint_for_payment(payment_event=payment_event)

    fees_account = CoinAccount.objects.get(account_key=SYSTEM_ACCOUNT_FEES)
    fees_account.status = CoinAccount.Status.SUSPENDED
    fees_account.save(update_fields=["status", "updated_at"])

    with pytest.raises(ValidationError):
        create_transfer(sender=sender, receiver=receiver, amount_cents=200)


@pytest.mark.django_db
def test_system_account_whitelist_rejects_unknown():
    user = User.objects.create_user(email="u15@example.com", password="pass1234", handle="u15", name="User Fifteen")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    CoinAccount.objects.get_or_create(
        account_key="system:bogus",
        defaults={"label": "Bogus", "is_system": True},
    )
    with pytest.raises(ValidationError):
        post_event_and_entries(
            event_type=CoinEvent.EventType.TRANSFER,
            created_by=None,
            entries=[
                {
                    "account_key": "system:bogus",
                    "amount_cents": 100,
                    "currency": "SLC",
                    "direction": CoinLedgerEntry.Direction.DEBIT,
                },
                {
                    "account_key": f"user:{user.id}",
                    "amount_cents": 100,
                    "currency": "SLC",
                    "direction": CoinLedgerEntry.Direction.CREDIT,
                },
            ],
        )


@pytest.mark.django_db
def test_unknown_account_key_rejected():
    user = User.objects.create_user(email="u9@example.com", password="pass1234", handle="u9", name="User Nine")
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )

    with pytest.raises(ValidationError):
        post_event_and_entries(
            event_type=CoinEvent.EventType.TRANSFER,
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


@pytest.mark.django_db
def test_user_delete_is_protected_by_coin_account():
    user = User.objects.create_user(
        email="protect@example.com",
        password="pass1234",
        handle="protect",
        name="Protect User",
    )
    CoinAccount.objects.get_or_create(
        user=user,
        defaults={"account_key": CoinAccount.user_account_key(user.id)},
    )
    with pytest.raises(ProtectedError):
        user.delete()
