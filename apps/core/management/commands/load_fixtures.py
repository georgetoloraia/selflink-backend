from __future__ import annotations

from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

DEFAULT_FIXTURE_DIR = Path("config/fixtures")


class Command(BaseCommand):
    help = "Load JSON fixtures from config/fixtures or a provided path"

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument(
            "--path",
            help="Directory containing fixture files (defaults to config/fixtures)",
        )
        parser.add_argument(
            "--using",
            default="default",
            help="Database alias to load fixtures into",
        )

    def handle(self, *args, **options):
        path_option = options.get("path")
        db_alias = options.get("using")
        fixture_dir = Path(path_option) if path_option else DEFAULT_FIXTURE_DIR
        if not fixture_dir.exists() or not fixture_dir.is_dir():
            raise CommandError(f"Fixture directory {fixture_dir} does not exist")

        fixtures = sorted(fixture_dir.glob("*.json"))
        if not fixtures:
            self.stdout.write(self.style.WARNING(f"No fixtures found in {fixture_dir}"))
            return

        for fixture in fixtures:
            self._load_fixture(fixture, db_alias)
        self.stdout.write(self.style.SUCCESS("Fixtures loaded."))

    def _load_fixture(self, fixture_path: Path, db_alias: str) -> None:
        if not fixture_path.exists():  # pragma: no cover - defensive
            raise CommandError(f"Fixture {fixture_path} not found")
        self.stdout.write(f"Loading {fixture_path.name}…")
        call_command("loaddata", str(fixture_path), database=db_alias)
