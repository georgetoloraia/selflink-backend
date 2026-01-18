from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import libs.idgen


def generate_reference() -> str:
    return uuid.uuid4().hex


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0005_payment_event_verified_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentevent",
            name="currency",
            field=models.CharField(default="USD", max_length=8),
        ),
        migrations.CreateModel(
            name="PaymentCheckout",
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
                    "provider",
                    models.CharField(
                        choices=[("stripe", "Stripe"), ("ipay", "iPay")],
                        max_length=32,
                    ),
                ),
                ("reference", models.CharField(default=generate_reference, max_length=64, unique=True)),
                ("amount_cents", models.PositiveIntegerField()),
                ("currency", models.CharField(default="USD", max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("paid", "Paid"),
                            ("failed", "Failed"),
                            ("canceled", "Canceled"),
                        ],
                        default="created",
                        max_length=16,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payment_checkouts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
