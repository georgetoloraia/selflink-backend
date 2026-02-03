from __future__ import annotations

from django.db import migrations, models


def seed_paid_products(apps, schema_editor):
    PaidProduct = apps.get_model("coin", "PaidProduct")
    products = [
        {
            "code": "premium_month",
            "title": "Premium (Monthly)",
            "description": "Unlock Premium features for 30 days.",
            "price_slc": 1000,
            "duration_days": 30,
            "entitlement_key": "premium",
            "is_active": True,
            "sort_order": 10,
        },
        {
            "code": "premium_plus_month",
            "title": "Premium+ (Monthly)",
            "description": "Unlock Premium+ features for 30 days.",
            "price_slc": 2000,
            "duration_days": 30,
            "entitlement_key": "premium_plus",
            "is_active": True,
            "sort_order": 20,
        },
    ]
    for payload in products:
        PaidProduct.objects.update_or_create(code=payload["code"], defaults=payload)


def unseed_paid_products(apps, schema_editor):
    PaidProduct = apps.get_model("coin", "PaidProduct")
    PaidProduct.objects.filter(code__in=["premium_month", "premium_plus_month"]).update(
        is_active=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("coin", "0002_coinaccount_user_protect"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaidProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=64, unique=True)),
                ("title", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True)),
                ("price_slc", models.BigIntegerField(help_text="SLC cents; integer smallest unit.")),
                ("duration_days", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "entitlement_key",
                    models.CharField(
                        choices=[("premium", "Premium"), ("premium_plus", "Premium Plus")],
                        max_length=32,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.IntegerField(default=0)),
            ],
            options={
                "ordering": ["sort_order", "price_slc"],
            },
        ),
        migrations.CreateModel(
            name="UserEntitlement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "key",
                    models.CharField(
                        choices=[("premium", "Premium"), ("premium_plus", "Premium Plus")],
                        max_length=32,
                    ),
                ),
                ("active_until", models.DateTimeField(blank=True, null=True)),
                ("source", models.CharField(default="slc", max_length=32)),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="entitlements",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "key")},
            },
        ),
        migrations.AddIndex(
            model_name="userentitlement",
            index=models.Index(fields=["user", "key"], name="coin_usere_user_id_55b5b0_idx"),
        ),
        migrations.RunPython(seed_paid_products, reverse_code=unseed_paid_products),
    ]
