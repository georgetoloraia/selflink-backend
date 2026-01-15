from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.coin.models import CoinAccount
from apps.users.models import User


class Command(BaseCommand):
    help = "Backfill CoinAccount rows for existing users (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--batch-size", type=int, default=1000, help="Users processed per batch.")

    def handle(self, *args, **options) -> None:
        batch_size = max(1, min(int(options.get("batch_size") or 1000), 10000))
        last_id = 0
        created_total = 0

        while True:
            user_ids = list(
                User.objects.filter(id__gt=last_id)
                .order_by("id")
                .values_list("id", flat=True)[:batch_size]
            )
            if not user_ids:
                break
            existing = set(
                CoinAccount.objects.filter(user_id__in=user_ids).values_list("user_id", flat=True)
            )
            to_create = [
                CoinAccount(user_id=user_id, account_key=CoinAccount.user_account_key(user_id))
                for user_id in user_ids
                if user_id not in existing
            ]
            with transaction.atomic():
                CoinAccount.objects.bulk_create(to_create, ignore_conflicts=True)
            created_total += len(to_create)
            last_id = user_ids[-1]
            self.stdout.write(f"processed_up_to_user_id={last_id} created={len(to_create)}")

        self.stdout.write(self.style.SUCCESS(f"coin_backfill_accounts complete: created={created_total}"))
