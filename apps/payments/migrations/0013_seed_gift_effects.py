from __future__ import annotations

from django.db import migrations


def upsert_gift(gift_model, *, key: str, defaults: dict) -> None:
    name = defaults.get("name")
    gift = gift_model.objects.filter(key=key).first()
    if not gift and name:
        gift = gift_model.objects.filter(name=name).first()
    if gift:
        for field, value in defaults.items():
            setattr(gift, field, value)
        if key and not gift.key:
            gift.key = key
        gift.save()
        return
    gift_model.objects.create(key=key, **defaults)


def seed_effect_gifts(apps, schema_editor) -> None:
    GiftType = apps.get_model("payments", "GiftType")

    upsert_gift(
        GiftType,
        key="border_lighting",
        defaults={
            "name": "Border Lighting",
            "price_cents": 100,
            "price_slc_cents": 100,
            "kind": "animated",
            "media_url": "/media/gifts/border-lighting.png",
            "animation_url": "/media/gifts/border-lighting.json",
            "is_active": True,
            "effects": {
                "version": 1,
                "persist": {"mode": "window", "window_seconds": 3600},
                "effects": [
                    {"type": "border_glow", "color": "#FFD166", "intensity": 0.8},
                    {"type": "burst", "style": "lottie"},
                ],
            },
        },
    )

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


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0012_gifttype_effects"),
    ]

    operations = [
        migrations.RunPython(seed_effect_gifts, noop_reverse),
    ]
