from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.contrib_rewards.services.payout import generate_monthly_payout


class Command(BaseCommand):
    help = "Compute deterministic payout CSV + manifest for a given month (dry-run only)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--month", required=True, help="Target month in YYYY-MM format.")
        parser.add_argument("--ruleset", default="v1", help="Ruleset version (default v1).")
        parser.add_argument("--output-dir", type=str, default=None, help="Optional output directory.")

    def handle(self, *args, **options):
        month = options["month"]
        ruleset = options["ruleset"]
        output_dir = options.get("output_dir")

        try:
            csv_text, inputs_hash, outputs_hash, summary = generate_monthly_payout(
                month=month,
                ruleset_version=ruleset,
                dry_run=True,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        base_dir = Path(output_dir) if output_dir else Path(settings.MEDIA_ROOT) / "rewards_payouts" / month
        base_dir.mkdir(parents=True, exist_ok=True)

        csv_path = base_dir / "payout.csv"
        csv_path.write_text(csv_text)

        manifest = {
            "month": month,
            "ruleset_version": ruleset,
            "inputs_hash": inputs_hash,
            "outputs_hash": outputs_hash,
            "user_count": summary.get("user_count", 0),
            "total_points": summary.get("total_points", 0),
        }
        manifest_path = base_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2))

        self.stdout.write(self.style.SUCCESS(f"Wrote payout CSV to {csv_path.resolve()}"))
        self.stdout.write(self.style.SUCCESS(f"Wrote manifest to {manifest_path.resolve()}"))
        self.stdout.write(self.style.SUCCESS(f"inputs_hash={inputs_hash} outputs_hash={outputs_hash}"))
