from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0004_personalmapprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContributorProfile",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        default=libs.idgen.generate_id,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("github_username", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contributor_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"indexes": [models.Index(fields=["github_username"], name="contrib_re_github__a562a7_idx")]},
        ),
        migrations.CreateModel(
            name="MonthlyRewardSnapshot",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        default=libs.idgen.generate_id,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("period", models.CharField(help_text="YYYY-MM", max_length=7, unique=True)),
                ("revenue_cents", models.PositiveIntegerField(default=0)),
                ("costs_cents", models.PositiveIntegerField(default=0)),
                ("contributor_pool_cents", models.PositiveIntegerField(default=0)),
                ("total_points", models.IntegerField(default=0)),
                ("total_events", models.PositiveIntegerField(default=0)),
                ("ledger_hash", models.CharField(help_text="SHA256 hash of ordered ledger for auditing.", max_length=128)),
                ("dispute_window_ends_at", models.DateTimeField()),
            ],
            options={"ordering": ["-period"]},
        ),
        migrations.CreateModel(
            name="RewardEvent",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        default=libs.idgen.generate_id,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("pr_merged", "PR merged"),
                            ("bounty_paid", "Bounty paid"),
                            ("manual_adjustment", "Manual adjustment"),
                            ("bonus", "Bonus"),
                            ("penalty", "Penalty"),
                        ],
                        max_length=64,
                    ),
                ),
                ("points", models.IntegerField(help_text="Positive for rewards, negative for clawbacks.")),
                ("occurred_at", models.DateTimeField(default=timezone.now)),
                (
                    "reference",
                    models.CharField(
                        blank=True,
                        help_text="External reference such as PR number or bounty id.",
                        max_length=255,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("notes", models.CharField(blank=True, max_length=255)),
                (
                    "contributor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events",
                        to="contrib_rewards.contributorprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["contributor", "occurred_at"], name="contrib_re_contribu_62a2aa_idx"),
                    models.Index(fields=["event_type", "occurred_at"], name="contrib_re_event_ty_71bfa1_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Payout",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        default=libs.idgen.generate_id,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("points", models.IntegerField()),
                ("amount_cents", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("paid", "Paid"),
                            ("canceled", "Canceled"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "contributor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payouts",
                        to="contrib_rewards.contributorprofile",
                    ),
                ),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payouts",
                        to="contrib_rewards.monthlyrewardsnapshot",
                    ),
                ),
            ],
            options={
                "unique_together": {("snapshot", "contributor")},
                "indexes": [
                    models.Index(fields=["snapshot", "status"], name="contrib_re_snapsho_aa39e9_idx"),
                    models.Index(fields=["contributor", "status"], name="contrib_re_contribu_4d5990_idx"),
                ],
            },
        ),
    ]
