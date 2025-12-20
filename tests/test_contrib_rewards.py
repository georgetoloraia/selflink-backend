from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.contrib_rewards.models import ContributorProfile, MonthlyRewardSnapshot, RewardEvent
from apps.contrib_rewards.services import calculate_monthly_rewards
from apps.users.models import User


@pytest.mark.django_db
def test_reward_event_is_immutable():
    user = User.objects.create_user(email="u1@example.com", password="pass1234", handle="user1", name="User One")
    contributor = ContributorProfile.objects.create(user=user, github_username="user1")

    event = RewardEvent.objects.create(
        contributor=contributor,
        event_type=RewardEvent.EventType.PR_MERGED,
        points=10,
        reference="PR-1",
    )

    event.points = 5
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()


@pytest.mark.django_db
def test_monthly_rewards_dry_run_allocates_pool():
    user = User.objects.create_user(email="u2@example.com", password="pass1234", handle="user2", name="User Two")
    contributor = ContributorProfile.objects.create(user=user, github_username="user2")
    RewardEvent.objects.create(
        contributor=contributor,
        event_type=RewardEvent.EventType.PR_MERGED,
        points=10,
        occurred_at=datetime(2025, 1, 15, tzinfo=dt_timezone.utc),
    )

    result = calculate_monthly_rewards(
        period="2025-01",
        revenue_cents=10_000,
        costs_cents=2_000,
        dry_run=True,
    )

    assert result.total_points == 10
    assert result.total_events == 1
    assert result.contributor_pool_cents == 4_000
    assert len(result.payouts) == 1
    assert result.payouts[0].amount_cents == 4_000
    assert result.ledger_hash
    assert result.snapshot is None


@pytest.mark.django_db
def test_rewards_snapshot_is_deterministic():
    user = User.objects.create_user(email="det@example.com", password="pass1234", handle="det", name="Deterministic")
    contributor = ContributorProfile.objects.create(user=user, github_username="det")
    RewardEvent.objects.create(
        contributor=contributor,
        event_type=RewardEvent.EventType.PR_MERGED,
        points=7,
        occurred_at=datetime(2025, 2, 10, tzinfo=dt_timezone.utc),
    )

    first = calculate_monthly_rewards(period="2025-02", revenue_cents=0, costs_cents=0, dry_run=True)
    second = calculate_monthly_rewards(period="2025-02", revenue_cents=0, costs_cents=0, dry_run=True)

    assert first.ledger_hash == second.ledger_hash
    assert first.csv_bytes == second.csv_bytes


@pytest.mark.django_db
def test_monthly_snapshot_is_immutable():
    snapshot = MonthlyRewardSnapshot.objects.create(
        period="2025-03",
        revenue_cents=0,
        costs_cents=0,
        contributor_pool_cents=0,
        total_points=0,
        total_events=0,
        ledger_hash="hash",
        dispute_window_ends_at=timezone.now(),
    )
    snapshot.total_points = 5
    with pytest.raises(ValidationError):
        snapshot.save()
    with pytest.raises(ValidationError):
        snapshot.delete()
