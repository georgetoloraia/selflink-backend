from __future__ import annotations

from django.db import migrations


def normalize_effects(apps, schema_editor) -> None:
    GiftType = apps.get_model("payments", "GiftType")

    GiftType.objects.filter(key="border_lighting").update(
        effects={
            "version": 2,
            "persist": {"mode": "window", "window_seconds": 3600},
            "effects": [
                {
                    "type": "overlay",
                    "scope": "post",
                    "clip_to_bounds": True,
                    "z_index": 5,
                    "opacity": 0.9,
                    "animation": "/media/gifts/border-lighting.json",
                    "fit": "cover",
                    "loop": True,
                    "duration_ms": 12000,
                },
                {"type": "border_glow", "color": "#FFD166", "intensity": 0.8},
            ],
        }
    )

    GiftType.objects.filter(key="super_like").update(
        effects={
            "version": 2,
            "persist": {"mode": "window", "window_seconds": 86400},
            "effects": [
                {
                    "type": "overlay",
                    "scope": "post",
                    "clip_to_bounds": True,
                    "z_index": 5,
                    "opacity": 0.9,
                    "animation": "/media/gifts/super-like.json",
                    "fit": "cover",
                    "loop": True,
                    "duration_ms": 12000,
                },
                {"type": "highlight", "color": "#FF4D6D"},
                {"type": "badge", "text": "Super Like"},
            ],
        }
    )


def noop_reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0015_gifttype_url_charfields"),
    ]

    operations = [
        migrations.RunPython(normalize_effects, noop_reverse),
    ]
