from __future__ import annotations

from django.db import migrations


def seed_test_gift(apps, schema_editor) -> None:
    GiftType = apps.get_model("payments", "GiftType")
    GiftType.objects.update_or_create(
        key="test_heart_1usd",
        defaults={
            "name": "Test Heart",
            "price_cents": 100,
            "price_slc_cents": 100,
            "kind": "static",
            "art_url": "/media/gifts/test-heart.png",
            "media_url": "/media/gifts/test-heart.png",
            "animation_url": "",
            "is_active": True,
            "metadata": {"seed": "migration", "purpose": "test"},
        },
    )


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0010_gifttype_fields"),
    ]

    operations = [
        migrations.RunPython(seed_test_gift, noop_reverse),
    ]
