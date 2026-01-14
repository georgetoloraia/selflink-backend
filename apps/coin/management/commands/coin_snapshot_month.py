from __future__ import annotations

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.coin.services.snapshot import generate_monthly_coin_snapshot


class Command(BaseCommand):
    help = "Generate a deterministic SLC ledger snapshot CSV + manifest for a given month."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--month", required=True, help="Target month in YYYY-MM format.")
        parser.add_argument("--dry-run", action="store_true", default=False, help="Skip DB snapshot write.")
        parser.add_argument("--output-dir", type=str, default=None, help="Optional output directory.")

    def handle(self, *args, **options):
        month: str = options["month"]
        output_dir = options.get("output_dir")
        dry_run = options["dry_run"]

        try:
            result = generate_monthly_coin_snapshot(
                period=month,
                dry_run=dry_run,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        base_dir = Path(output_dir) if output_dir else Path(settings.MEDIA_ROOT) / "coin_snapshots" / month
        base_dir.mkdir(parents=True, exist_ok=True)

        csv_path = base_dir / "snapshot.csv"
        csv_path.write_bytes(result.csv_bytes)

        csv_hash = hashlib.sha256(result.csv_bytes).hexdigest()
        manifest = {
            "period": result.period,
            "ledger_hash": result.ledger_hash,
            "csv_sha256": csv_hash,
            "total_events": result.total_events,
            "total_entries": result.total_entries,
            "total_volume_cents": result.total_volume_cents,
        }

        manifest_path = base_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2))

        self.stdout.write(self.style.SUCCESS(f"Wrote snapshot CSV to {csv_path.resolve()}"))
        self.stdout.write(self.style.SUCCESS(f"Wrote manifest to {manifest_path.resolve()}"))
        self.stdout.write(self.style.SUCCESS(f"ledger_hash={result.ledger_hash} csv_sha256={csv_hash}"))
