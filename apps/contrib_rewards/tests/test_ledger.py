from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.contrib_rewards.models import LedgerEntry, RewardEvent
from apps.contrib_rewards.services.ledger import post_event_and_ledger_entries
from apps.contrib_rewards.models import ContributorProfile
from apps.users.models import User


@pytest.mark.django_db
def test_balanced_transaction_succeeds():
    user = User.objects.create_user(email="u1@example.com", password="pass1234", handle="u1", name="User One")
    contributor = ContributorProfile.objects.create(user=user, github_username="u1")

    event = post_event_and_ledger_entries(
        event_type=RewardEvent.EventType.MANUAL_ADJUSTMENT,
        actor=contributor.user,
        entries=[
            {"account": "platform:rewards_pool", "amount": 10, "currency": "POINTS", "direction": LedgerEntry.Direction.DEBIT},
            {"account": "user:1", "amount": 10, "currency": "POINTS", "direction": LedgerEntry.Direction.CREDIT},
        ],
    )
    entries = list(event.ledger_entries.all())
    assert len(entries) == 2
    credits = [e for e in entries if e.direction == LedgerEntry.Direction.CREDIT]
    debits = [e for e in entries if e.direction == LedgerEntry.Direction.DEBIT]
    assert sum(e.amount for e in credits) == sum(e.amount for e in debits)


@pytest.mark.django_db
def test_unbalanced_transaction_raises():
    user = User.objects.create_user(email="u2@example.com", password="pass1234", handle="u2", name="User Two")
    ContributorProfile.objects.create(user=user, github_username="u2")
    with pytest.raises(ValidationError):
        post_event_and_ledger_entries(
            event_type=RewardEvent.EventType.MANUAL_ADJUSTMENT,
            actor=user,
            entries=[
                {"account": "platform:rewards_pool", "amount": 5, "currency": "POINTS", "direction": LedgerEntry.Direction.DEBIT},
                {"account": "user:2", "amount": 3, "currency": "POINTS", "direction": LedgerEntry.Direction.CREDIT},
            ],
        )
    assert RewardEvent.objects.count() == 0
    assert LedgerEntry.objects.count() == 0


@pytest.mark.django_db
def test_immutability():
    user = User.objects.create_user(email="u3@example.com", password="pass1234", handle="u3", name="User Three")
    contributor = ContributorProfile.objects.create(user=user, github_username="u3")
    event = post_event_and_ledger_entries(
        event_type=RewardEvent.EventType.MANUAL_ADJUSTMENT,
        actor=contributor.user,
        entries=[
            {"account": "platform:rewards_pool", "amount": 2, "currency": "POINTS", "direction": LedgerEntry.Direction.DEBIT},
            {"account": "user:3", "amount": 2, "currency": "POINTS", "direction": LedgerEntry.Direction.CREDIT},
        ],
    )
    with pytest.raises(ValidationError):
        event.save()
    entry = event.ledger_entries.first()
    assert entry is not None
    with pytest.raises(ValidationError):
        entry.save()
