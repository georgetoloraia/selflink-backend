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
            name="MentorProfile",
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
                ("tone", models.CharField(default="gentle", max_length=32)),
                ("level", models.CharField(default="basic", max_length=32)),
                ("preferences", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="mentor_profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MentorSession",
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
                ("question", models.TextField()),
                ("answer", models.TextField()),
                ("sentiment", models.CharField(blank=True, max_length=32)),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="mentor_sessions", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DailyTask",
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
                ("task", models.CharField(max_length=255)),
                ("due_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("completed", "Completed"), ("skipped", "Skipped")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="daily_tasks", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]
