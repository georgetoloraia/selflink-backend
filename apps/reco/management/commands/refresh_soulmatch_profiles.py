from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.reco.services import refresh_soulmatch_profile
from apps.users.models import User


class Command(BaseCommand):
    help = "Recompute SoulMatch profiles for all or specific users"

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument(
            "--user",
            type=int,
            help="Target user ID",
        )

    def handle(self, *args, **options):
        user_id = options.get("user")
        if user_id:
            user = User.objects.get(id=user_id)
            refresh_soulmatch_profile(user)
            self.stdout.write(self.style.SUCCESS(f"Refreshed profile for {user_id}"))
            return

        queryset = User.objects.all()
        for user in queryset.iterator():
            refresh_soulmatch_profile(user)
        self.stdout.write(self.style.SUCCESS("Refreshed profiles for all users"))
