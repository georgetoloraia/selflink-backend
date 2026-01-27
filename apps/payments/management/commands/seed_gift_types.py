from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.payments.models import GiftType


class Command(BaseCommand):
    help = "Seed default GiftType rows (idempotent)."

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[2]
        preset_path = base_dir / "fixtures" / "gift_effects" / "snowfall_in_post_v2.json"
        if not preset_path.exists():
            self.stderr.write(f"Missing preset file: {preset_path}")
            return

        effects = json.loads(preset_path.read_text(encoding="utf-8"))

        gift, created = GiftType.objects.update_or_create(
            key="winter_snow",
            defaults={
                "name": "Winter Snow",
                "price_cents": 100,
                "price_slc_cents": 100,
                "kind": GiftType.Kind.ANIMATED,
                "media_url": "/static/gifts/snowfall.png",
                "animation_url": "/static/gifts/snowfall.json",
                "is_active": True,
                "effects": effects,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} gift {gift.key} (id={gift.id})")
