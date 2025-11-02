from __future__ import annotations

from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AstroProfile",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        default=libs.idgen.generate_id,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sun", models.CharField(blank=True, max_length=32)),
                ("moon", models.CharField(blank=True, max_length=32)),
                ("ascendant", models.CharField(blank=True, max_length=32)),
                ("planets", models.JSONField(blank=True, default=dict)),
                ("aspects", models.JSONField(blank=True, default=dict)),
                ("houses", models.JSONField(blank=True, default=dict)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="astro_profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MatrixData",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        default=libs.idgen.generate_id,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("life_path", models.CharField(blank=True, max_length=32)),
                ("traits", models.JSONField(blank=True, default=dict)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="matrix_data", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]
