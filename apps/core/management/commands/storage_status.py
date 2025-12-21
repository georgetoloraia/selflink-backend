from __future__ import annotations

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Report effective storage backend configuration and sample URL output."

    def handle(self, *args, **options):
        storage_backend = getattr(settings, "STORAGE_BACKEND", "local")
        default_storage_setting = getattr(settings, "DEFAULT_FILE_STORAGE", "(default)")
        storage_backend_path = f"{default_storage.__class__.__module__}.{default_storage.__class__.__name__}"

        self.stdout.write(f"STORAGE_BACKEND={storage_backend}")
        self.stdout.write(f"DEFAULT_FILE_STORAGE={default_storage_setting}")
        self.stdout.write(f"DEFAULT_STORAGE_BACKEND={storage_backend_path}")

        if storage_backend == "local":
            self.stdout.write(f"MEDIA_ROOT={getattr(settings, 'MEDIA_ROOT', '')}")
            self.stdout.write(f"MEDIA_URL={getattr(settings, 'MEDIA_URL', '')}")
            expected = "django.core.files.storage.FileSystemStorage"
        elif storage_backend == "s3":
            self.stdout.write(f"S3_ENDPOINT={getattr(settings, 'AWS_S3_ENDPOINT_URL', '')}")
            self.stdout.write(f"S3_BUCKET={getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')}")
            expected = "storages.backends.s3boto3.S3Boto3Storage"
        else:
            raise CommandError(f"Unsupported STORAGE_BACKEND={storage_backend}")

        configured_backend = settings.STORAGES.get("default", {}).get("BACKEND")
        if configured_backend and configured_backend != expected:
            raise CommandError(
                f"Inconsistent storage backend: STORAGES.default={configured_backend} expected {expected}"
            )
        if default_storage_setting not in ("(default)", expected):
            raise CommandError(
                f"Inconsistent DEFAULT_FILE_STORAGE={default_storage_setting}; expected {expected}"
            )
        if storage_backend_path != expected:
            raise CommandError(
                f"Inconsistent default_storage={storage_backend_path}; expected {expected}"
            )

        sample_path = "storage-status/sample.txt"
        try:
            sample_url = default_storage.url(sample_path)
        except Exception as exc:  # pragma: no cover - surfaces config issues
            raise CommandError(f"Failed to build storage URL: {exc}") from exc
        self.stdout.write(f"SAMPLE_PATH={sample_path}")
        self.stdout.write(f"SAMPLE_URL={sample_url}")
