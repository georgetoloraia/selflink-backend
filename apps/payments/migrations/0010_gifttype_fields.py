from __future__ import annotations

from django.db import migrations, models


def copy_price_slc_cents(apps, schema_editor) -> None:
    GiftType = apps.get_model("payments", "GiftType")
    GiftType.objects.filter(price_slc_cents=0).update(price_slc_cents=models.F("price_cents"))


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0009_payment_event_iap_providers"),
    ]

    operations = [
        migrations.AddField(
            model_name="gifttype",
            name="key",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="gifttype",
            name="price_slc_cents",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="gifttype",
            name="kind",
            field=models.CharField(
                choices=[("static", "Static"), ("animated", "Animated")],
                default="static",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="gifttype",
            name="media_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="gifttype",
            name="animation_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="gifttype",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(copy_price_slc_cents, noop_reverse),
    ]
