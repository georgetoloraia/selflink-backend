from __future__ import annotations

import uuid

from django.db import migrations, models
import django.db.models.deletion

import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("contrib_rewards", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LedgerEntry",
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
                ("account", models.CharField(db_index=True, max_length=255)),
                ("amount", models.BigIntegerField(help_text="Smallest unit, e.g. integer points.")),
                ("currency", models.CharField(default="POINTS", max_length=16)),
                ("direction", models.CharField(choices=[("DEBIT", "Debit"), ("CREDIT", "Credit")], max_length=6)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ledger_entries",
                        to="contrib_rewards.rewardevent",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="ledgerentry",
            index=models.Index(fields=["account", "created_at"], name="contrib_re_account__77dc1d_idx"),
        ),
        migrations.AddIndex(
            model_name="ledgerentry",
            index=models.Index(fields=["tx_id"], name="contrib_re_tx_id_abbde3_idx"),
        ),
    ]
