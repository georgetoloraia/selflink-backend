from __future__ import annotations

import io

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.contrib_rewards.models import ContributorProfile, LedgerEntry, RewardEvent
from apps.contrib_rewards.services.ledger import post_event_and_ledger_entries
from apps.contrib_rewards.services.payout import generate_monthly_payout
from apps.users.models import User


@pytest.mark.django_db
def test_payout_command_dry_run_hash_stable():
    month = timezone.now().strftime("%Y-%m")

    user1 = User.objects.create_user(email="u1@example.com", password="pass1234", handle="u1", name="User One")
    user2 = User.objects.create_user(email="u2@example.com", password="pass1234", handle="u2", name="User Two")
    ContributorProfile.objects.create(user=user1, github_username="u1")
    ContributorProfile.objects.create(user=user2, github_username="u2")

    # Two users with different point totals.
    post_event_and_ledger_entries(
        event_type=RewardEvent.EventType.MANUAL_ADJUSTMENT,
        entries=[
            {"account": "platform:rewards_pool", "amount": 15, "currency": "POINTS", "direction": LedgerEntry.Direction.DEBIT},
            {"account": f"user:{user1.id}", "amount": 10, "currency": "POINTS", "direction": LedgerEntry.Direction.CREDIT},
            {"account": f"user:{user2.id}", "amount": 5, "currency": "POINTS", "direction": LedgerEntry.Direction.CREDIT},
        ],
    )

    out1 = io.StringIO()
    call_command("rewards_payout", "--month", month, "--dry-run", stdout=out1)
    output1 = out1.getvalue()
    assert "inputs_hash=" in output1
    assert "outputs_hash=" in output1

    out2 = io.StringIO()
    call_command("rewards_payout", "--month", month, "--dry-run", stdout=out2)
    output2 = out2.getvalue()
    assert output1 == output2

    csv_text, _, _, _ = generate_monthly_payout(month=month, ruleset_version="v1", dry_run=True)
    assert "user_id,points" in csv_text
    assert f"{user1.id},10" in csv_text
    assert f"{user2.id},5" in csv_text
