from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Print MEDIA_ROOT and verify a relative media path exists."

    def add_arguments(self, parser) -> None:
        parser.add_argument("relative_path", help="Path relative to MEDIA_ROOT, e.g. avatars/uuid.jpeg")

    def handle(self, *args, **options):
        relative_path = options["relative_path"]
        media_root = Path(settings.MEDIA_ROOT).resolve()
        candidate = (media_root / relative_path).resolve()

        if media_root not in candidate.parents and candidate != media_root:
            raise CommandError("Path must be inside MEDIA_ROOT.")

        exists = candidate.exists()
        self.stdout.write(f"MEDIA_ROOT={media_root}")
        self.stdout.write(f"PATH={candidate}")
        self.stdout.write(f"EXISTS={exists}")

        if not exists:
            raise CommandError("File does not exist.")
