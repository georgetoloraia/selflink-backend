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


def seed_trendy_gifts(apps, schema_editor) -> None:
    GiftType = apps.get_model("payments", "GiftType")

    gifts = [
        {
            "key": "super_like_gold_1usd",
            "defaults": {
                "name": "Super Like",
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
        },
        {
            "key": "rain_effect_099",
            "defaults": {
                "name": "Rain",
                "kind": "animated",
                "animation_url": "/media/gifts/trendy/rain.json",
                "media_url": "/media/gifts/trendy/rain.png",
                "price_cents": 99,
                "price_slc_cents": 99,
                "is_active": True,
                "effects": {
                    "version": 2,
                    "persist": {"mode": "none", "window_seconds": 0},
                    "effects": [
                        {
                            "type": "overlay",
                            "scope": "post",
                            "animation": "/media/gifts/trendy/rain.json",
                        }
                    ],
                },
            },
        },
        {
            "key": "sparkles_049",
            "defaults": {
                "name": "Sparkles",
                "kind": "animated",
                "animation_url": "/media/gifts/trendy/sparkles.json",
                "media_url": "/media/gifts/trendy/heart.png",
                "price_cents": 49,
                "price_slc_cents": 49,
                "is_active": True,
                "effects": {
                    "version": 2,
                    "persist": {"mode": "none", "window_seconds": 0},
                    "effects": [
                        {
                            "type": "overlay",
                            "scope": "post",
                            "animation": "/media/gifts/trendy/sparkles.json",
                        }
                    ],
                },
            },
        },
        {
            "key": "heart_burst_049",
            "defaults": {
                "name": "Heart Burst",
                "kind": "animated",
                "animation_url": "/media/gifts/trendy/heart_burst.json",
                "media_url": "/media/gifts/trendy/heart.png",
                "price_cents": 49,
                "price_slc_cents": 49,
                "is_active": True,
                "effects": {
                    "version": 2,
                    "persist": {"mode": "none", "window_seconds": 0},
                    "effects": [
                        {
                            "type": "overlay",
                            "scope": "post",
                            "animation": "/media/gifts/trendy/heart_burst.json",
                        }
                    ],
                },
            },
        },
        {
            "key": "crown_199",
            "defaults": {
                "name": "Crown",
                "kind": "static",
                "animation_url": "",
                "media_url": "/media/gifts/trendy/crown.png",
                "price_cents": 199,
                "price_slc_cents": 199,
                "is_active": True,
                "effects": {
                    "version": 2,
                    "persist": {"mode": "window", "window_seconds": 86400},
                    "effects": [
                        {
                            "type": "badge",
                            "scope": "post",
                            "text": "Crowned",
                        },
                        {
                            "type": "border_glow",
                            "scope": "post",
                            "color": "#FFD54A",
                            "intensity": 0.6,
                        },
                    ],
                },
            },
        },
        {
            "key": "trending_flame_149",
            "defaults": {
                "name": "Trending Flame",
                "kind": "static",
                "animation_url": "",
                "media_url": "/media/gifts/trendy/flame.png",
                "price_cents": 149,
                "price_slc_cents": 149,
                "is_active": True,
                "effects": {
                    "version": 2,
                    "persist": {"mode": "window", "window_seconds": 7200},
                    "effects": [
                        {
                            "type": "badge",
                            "scope": "post",
                            "text": "Trending",
                        },
                        {
                            "type": "highlight",
                            "scope": "post",
                            "tone": "warm",
                        },
                    ],
                },
            },
        },
        {
            "key": "megaphone_comment_199",
            "defaults": {
                "name": "Megaphone",
                "kind": "static",
                "animation_url": "",
                "media_url": "/media/gifts/trendy/megaphone.png",
                "price_cents": 199,
                "price_slc_cents": 199,
                "is_active": True,
                "effects": {
                    "version": 2,
                    "persist": {"mode": "window", "window_seconds": 1800},
                    "effects": [
                        {
                            "type": "highlight",
                            "scope": "comment",
                            "tone": "neon",
                        },
                        {
                            "type": "badge",
                            "scope": "comment",
                            "text": "Highlighted",
                        },
                    ],
                },
            },
        },
        {
            "key": "spotlight_499",
            "defaults": {
                "name": "Spotlight",
                "kind": "animated",
                "animation_url": "/media/gifts/trendy/spotlight.json",
                "media_url": "/media/gifts/trendy/heart.png",
                "price_cents": 499,
                "price_slc_cents": 499,
                "is_active": True,
                "effects": {
                    "version": 2,
                    "persist": {"mode": "window", "window_seconds": 3600},
                    "effects": [
                        {
                            "type": "highlight",
                            "scope": "post",
                            "tone": "spotlight",
                        },
                        {
                            "type": "overlay",
                            "scope": "post",
                            "animation": "/media/gifts/trendy/spotlight.json",
                        },
                    ],
                },
            },
        },
    ]

    for entry in gifts:
        upsert_gift(GiftType, key=entry["key"], defaults=entry["defaults"])


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0016_normalize_gift_effects_v2"),
    ]

    operations = [
        migrations.RunPython(seed_trendy_gifts, noop_reverse),
    ]
