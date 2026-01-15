from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("coin", "0001_initial"),
        ("payments", "0003_plan_external_price_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentEvent",
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
                    models.CharField(choices=[("stripe", "Stripe")], max_length=32),
                ),
                ("provider_event_id", models.CharField(max_length=128)),
                ("event_type", models.CharField(blank=True, max_length=64)),
                ("amount_cents", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[("received", "Received"), ("minted", "Minted"), ("failed", "Failed")],
                        default="received",
                        max_length=16,
                    ),
                ),
                ("raw_body_hash", models.CharField(max_length=64)),
                (
                    "minted_coin_event",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payment_events",
                        to="coin.coinevent",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payment_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"unique_together": {("provider", "provider_event_id")}},
        ),
    ]
