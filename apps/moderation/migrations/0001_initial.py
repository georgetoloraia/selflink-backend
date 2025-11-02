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
            name="Report",
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
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("post", "Post"),
                            ("comment", "Comment"),
                            ("message", "Message"),
                        ],
                        max_length=32,
                    ),
                ),
                ("target_id", models.BigIntegerField()),
                ("reason", models.CharField(max_length=255)),
                ("status", models.CharField(default="open", max_length=32)),
                ("notes", models.TextField(blank=True)),
                (
                    "reporter",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="reports_made", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Enforcement",
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
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("post", "Post"),
                            ("comment", "Comment"),
                            ("message", "Message"),
                        ],
                        max_length=32,
                    ),
                ),
                ("target_id", models.BigIntegerField()),
                (
                    "action",
                    models.CharField(
                        choices=[("warn", "Warn"), ("suspend", "Suspend"), ("ban", "Ban")],
                        max_length=32,
                    ),
                ),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
