from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.contrib_rewards.services import calculate_monthly_rewards


class Command(BaseCommand):
    help = "Calculate monthly contributor rewards and payouts from immutable ledger events."

    def add_arguments(self, parser) -> None:
        parser.add_argument("period", help="Target period in YYYY-MM format (e.g. 2025-01).")
        parser.add_argument("--revenue-cents", type=int, default=0, help="Gross revenue for the month in cents.")
        parser.add_argument("--costs-cents", type=int, default=0, help="Direct costs for the month in cents.")
        parser.add_argument(
            "--pool-percent",
            type=int,
            default=50,
            help="Percent of net revenue allocated to contributors (default 50).",
        )
        parser.add_argument(
            "--dispute-days",
            type=int,
            default=7,
            help="Days after month end to keep the dispute window open.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write snapshots/payouts, only print summary and CSV/hash.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Optional path to write the reproducible CSV ledger for the period.",
        )

    def handle(self, *args, **options):
        period: str = options["period"]
        dry_run: bool = options["dry_run"]
        output_path = options.get("output")

        try:
            result = calculate_monthly_rewards(
                period=period,
                revenue_cents=options["revenue_cents"],
                costs_cents=options["costs_cents"],
                pool_percent=options["pool_percent"],
                dispute_window_days=options["dispute_days"],
                dry_run=dry_run,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        if output_path:
            path = Path(output_path)
            path.write_bytes(result.csv_bytes)
            self.stdout.write(self.style.NOTICE(f"Wrote ledger CSV to {path.resolve()}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Ledger hash: {result.ledger_hash}\n"
                f"Total events: {result.total_events}, points: {result.total_points}\n"
                f"Pool: {result.contributor_pool_cents} cents from revenue={result.revenue_cents}, costs={result.costs_cents}"
            )
        )

        if not result.payouts:
            self.stdout.write("No payouts for this period (no points or events).")
        else:
            self.stdout.write("Payouts:")
            for payout in sorted(result.payouts, key=lambda p: (-p.amount_cents, p.contributor.id)):
                self.stdout.write(
                    f" - contributor={payout.contributor.id} points={payout.points} amount_cents={payout.amount_cents}"
                )

        if result.snapshot:
            self.stdout.write(self.style.SUCCESS(f"Snapshot stored: {result.snapshot.id}"))
        elif dry_run:
            self.stdout.write("Dry-run mode: no database writes performed.")
