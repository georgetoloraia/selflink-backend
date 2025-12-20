from __future__ import annotations

import pathlib
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.contrib_rewards.models import MonthlyRewardSnapshot
from apps.contrib_rewards.services.payout import generate_monthly_payout


class Command(BaseCommand):
    help = "Generate deterministic monthly rewards CSV and hashes from the contrib_rewards ledger."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--month", required=True, help="Target month in YYYY-MM format.")
        parser.add_argument("--ruleset", default="v1", help="Ruleset version (default v1).")
        parser.add_argument("--dry-run", action="store_true", default=False, help="Dry-run mode (default: off).")
        parser.add_argument(
            "--write-snapshot",
            action="store_true",
            default=False,
            help="Write or update a MonthlyRewardSnapshot row (skipped in dry-run unless this flag is set).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="(Deprecated) Snapshots are immutable; use a new period instead.",
        )
        parser.add_argument("--out", type=str, default=None, help="Optional path to write the CSV output.")

    def handle(self, *args, **options):
        month = options["month"]
        ruleset = options["ruleset"]
        dry_run = options["dry_run"]
        write_snapshot = options["write_snapshot"]
        out_path = options.get("out")

        try:
            datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
        except Exception as exc:
            raise CommandError("Month must be in YYYY-MM format.") from exc

        try:
            csv_text, inputs_hash, outputs_hash, summary = generate_monthly_payout(
                month=month,
                ruleset_version=ruleset,
                dry_run=dry_run,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        if out_path:
            path = pathlib.Path(out_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(csv_text)
            self.stdout.write(self.style.NOTICE(f"Wrote CSV to {path.resolve()}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"inputs_hash={inputs_hash} outputs_hash={outputs_hash} users={summary['user_count']} total_points={summary['total_points']}"
            )
        )

        if write_snapshot and not dry_run:
            if MonthlyRewardSnapshot.objects.filter(period=month).exists():
                raise CommandError("Snapshot already exists for this period. Snapshots are immutable.")

            snapshot = MonthlyRewardSnapshot.objects.create(
                period=month,
                revenue_cents=0,
                costs_cents=0,
                contributor_pool_cents=0,
                total_points=summary["total_points"],
                total_events=0,
                ledger_hash=inputs_hash,
                dispute_window_ends_at=timezone.now(),
            )
            self.stdout.write(self.style.SUCCESS(f"Snapshot stored for {month} ({snapshot.id})"))
        elif write_snapshot and dry_run:
            self.stdout.write("Dry-run mode: snapshot not written (use without --dry-run to persist).")
