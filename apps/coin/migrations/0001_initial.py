from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone

import libs.idgen


def create_system_and_user_accounts(apps, schema_editor) -> None:
    CoinAccount = apps.get_model("coin", "CoinAccount")
    User = apps.get_model("users", "User")

    system_accounts = [
        ("system:fees", "Fees"),
        ("system:revenue", "Revenue"),
        ("system:mint", "Mint"),
    ]
    for key, label in system_accounts:
        CoinAccount.objects.get_or_create(
            account_key=key,
            defaults={"label": label, "is_system": True},
        )

    for user in User.objects.all().only("id"):
        key = f"user:{user.id}"
        CoinAccount.objects.get_or_create(
            user_id=user.id,
            defaults={"account_key": key},
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0007_backfill_userpii"),
    ]

    operations = [
        migrations.CreateModel(
            name="CoinAccount",
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
                ("account_key", models.CharField(max_length=255, unique=True)),
                ("label", models.CharField(blank=True, max_length=255)),
                ("is_system", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("suspended", "Suspended")],
                        default="active",
                        max_length=16,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coin_account",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"indexes": [models.Index(fields=["account_key"], name="coin_acc_account_key_idx")]},
        ),
        migrations.CreateModel(
            name="CoinEvent",
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
                            ("mint", "Mint"),
                            ("transfer", "Transfer"),
                            ("spend", "Spend"),
                            ("refund", "Refund"),
                        ],
                        max_length=32,
                    ),
                ),
                ("occurred_at", models.DateTimeField(default=timezone.now)),
                ("idempotency_key", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("ruleset_version", models.CharField(default="v1", max_length=16)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="coin_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-occurred_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="MonthlyCoinSnapshot",
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
                ("total_events", models.PositiveIntegerField(default=0)),
                ("total_entries", models.PositiveIntegerField(default=0)),
                ("total_volume_cents", models.BigIntegerField(default=0)),
                ("ledger_hash", models.CharField(help_text="SHA256 hash of ordered ledger for auditing.", max_length=128)),
            ],
            options={"ordering": ["-period"]},
        ),
        migrations.CreateModel(
            name="CoinLedgerEntry",
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
                ("tx_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("account_key", models.CharField(max_length=255)),
                ("amount_cents", models.BigIntegerField(help_text="Smallest unit in cents.")),
                ("currency", models.CharField(default="SLC", max_length=16)),
                (
                    "direction",
                    models.CharField(
                        choices=[("DEBIT", "Debit"), ("CREDIT", "Credit")],
                        max_length=6,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ledger_entries",
                        to="coin.coinevent",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
                "indexes": [models.Index(fields=["account_key", "created_at"], name="coin_led_account_key_created_at_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="coinledgerentry",
            constraint=models.CheckConstraint(
                check=models.Q(amount_cents__gt=0),
                name="coin_amount_cents_gt_0",
            ),
        ),
        migrations.RunPython(create_system_and_user_accounts, migrations.RunPython.noop),
    ]
