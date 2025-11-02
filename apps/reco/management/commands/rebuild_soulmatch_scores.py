from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.reco.scores import compute_soulmatch_scores
from apps.users.models import User


class Command(BaseCommand):
    help = "Recompute SoulMatch scores for all users or a specific user"

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument("--user", type=int, help="User ID to refresh")

    def handle(self, *args, **options):
        user_id = options.get("user")
        if user_id:
            user = User.objects.get(id=user_id)
            candidates = User.objects.exclude(id=user.id)[:100]
            compute_soulmatch_scores(user, candidates)
            self.stdout.write(self.style.SUCCESS(f"Refreshed scores for {user_id}"))
            return

        queryset = User.objects.all()
        for user in queryset.iterator():
            candidates = User.objects.exclude(id=user.id)[:100]
            compute_soulmatch_scores(user, candidates)
        self.stdout.write(self.style.SUCCESS("Refreshed scores for all users"))
