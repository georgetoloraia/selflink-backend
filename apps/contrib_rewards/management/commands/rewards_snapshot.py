from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.contrib_rewards.services import calculate_monthly_rewards


class Command(BaseCommand):
    help = "Generate a deterministic rewards snapshot CSV and store the monthly snapshot."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--month", required=True, help="Target month in YYYY-MM format.")
        parser.add_argument("--revenue-cents", type=int, default=0, help="Gross revenue in cents.")
        parser.add_argument("--costs-cents", type=int, default=0, help="Direct costs in cents.")
        parser.add_argument("--pool-percent", type=int, default=50, help="Contributor pool percent (default 50).")
        parser.add_argument("--dispute-days", type=int, default=7, help="Dispute window days after month end.")
        parser.add_argument("--output", type=str, default=None, help="Optional CSV output path.")

    def handle(self, *args, **options):
        month: str = options["month"]
        output_path = options.get("output")

        try:
            result = calculate_monthly_rewards(
                period=month,
                revenue_cents=options["revenue_cents"],
                costs_cents=options["costs_cents"],
                pool_percent=options["pool_percent"],
                dispute_window_days=options["dispute_days"],
                dry_run=False,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        if output_path:
            path = Path(output_path)
        else:
            path = Path.cwd() / "rewards_snapshots" / f"{month}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.csv_bytes)

        self.stdout.write(self.style.SUCCESS(f"Wrote snapshot CSV to {path.resolve()}"))
        self.stdout.write(self.style.SUCCESS(f"Ledger hash: {result.ledger_hash}"))
