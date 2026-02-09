from __future__ import annotations

from django.db import migrations


def upsert_gift(gift_model, *, key: str, defaults: dict) -> None:
    gift = gift_model.objects.filter(key=key).first()
    if gift:
        for field, value in defaults.items():
            setattr(gift, field, value)
        gift.save()
        return
    gift_model.objects.create(key=key, **defaults)


def repair_gift_types(apps, schema_editor) -> None:
    GiftType = apps.get_model("payments", "GiftType")

    # Ensure the base Super Like gift exists (effects v1).
    upsert_gift(
        GiftType,
        key="super_like",
        defaults={
            "name": "Super Like",
            "price_cents": 250,
            "price_slc_cents": 250,
            "kind": "animated",
            "media_url": "/media/gifts/super-like.png",
            "animation_url": "/media/gifts/super-like.json",
            "is_active": True,
            "effects": {
                "version": 1,
                "persist": {"mode": "window", "window_seconds": 86400},
                "effects": [
                    {"type": "highlight", "color": "#FF4D6D"},
                    {"type": "badge", "text": "Super Like"},
                    {"type": "burst", "style": "lottie"},
                ],
            },
        },
    )

    # Ensure the trendy Super Like variant uses a distinct name.
    upsert_gift(
        GiftType,
        key="super_like_gold_1usd",
        defaults={
            "name": "Super Like Gold",
            "kind": "animated",
            "animation_url": "/media/gifts/trendy/super_like.json",
            "media_url": "/media/gifts/trendy/heart.png",
            "price_cents": 100,
            "price_slc_cents": 100,
            "is_active": True,
            "effects": {
                "version": 2,
                "persist": {"mode": "window", "window_seconds": 3600},
                "effects": [
                    {
                        "type": "border_glow",
                        "scope": "post",
                        "color": "#FFD54A",
                        "intensity": 0.9,
                    },
                    {
                        "type": "highlight",
                        "scope": "post",
                        "tone": "gold",
                    },
                    {
                        "type": "overlay",
                        "scope": "post",
                        "animation": "/media/gifts/trendy/super_like.json",
                    },
                ],
            },
        },
    )


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0018_alter_paymentcheckout_reference"),
    ]

    operations = [
        migrations.RunPython(repair_gift_types, noop_reverse),
    ]
