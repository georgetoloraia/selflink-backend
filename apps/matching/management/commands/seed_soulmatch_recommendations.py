from __future__ import annotations

from datetime import date, time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import User


class Command(BaseCommand):
    help = "Seed users for SoulMatch recommendations (dev only)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--force", action="store_true", help="Allow running outside DEBUG.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options.get("force"):
            raise CommandError("Refusing to seed outside DEBUG. Use --force to override.")

        seeds = [
            {"email": "soulmatch_seed1@example.com", "handle": "soul_seed1", "name": "Seed One"},
            {"email": "soulmatch_seed2@example.com", "handle": "soul_seed2", "name": "Seed Two"},
            {"email": "soulmatch_seed3@example.com", "handle": "soul_seed3", "name": "Seed Three"},
            {"email": "soulmatch_seed4@example.com", "handle": "soul_seed4", "name": "Seed Four"},
            {"email": "soulmatch_seed5@example.com", "handle": "soul_seed5", "name": "Seed Five"},
        ]

        created_count = 0
        updated_count = 0
        for idx, seed in enumerate(seeds, start=1):
            user = User.objects.filter(email=seed["email"]).first()
            if not user:
                user = User.objects.filter(handle=seed["handle"]).first()
            if user:
                changed = False
                if not user.birth_date:
                    user.birth_date = date(1990, 1, min(idx, 28))
                    changed = True
                if not user.birth_time:
                    user.birth_time = time(9 + idx % 6, 30)
                    changed = True
                if not user.birth_place:
                    user.birth_place = "Tbilisi"
                    changed = True
                if changed:
                    user.save(update_fields=["birth_date", "birth_time", "birth_place"])
                    updated_count += 1
                continue

            user = User.objects.create_user(
                email=seed["email"],
                password="seedpass123",
                handle=seed["handle"],
                name=seed["name"],
                birth_date=date(1990, 1, min(idx, 28)),
                birth_time=time(9 + idx % 6, 30),
                birth_place="Tbilisi",
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded SoulMatch users. Created: {created_count}, Updated: {updated_count}."
            )
        )
