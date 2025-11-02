from __future__ import annotations

from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("mentor", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MentorMemory",
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
                ("notes", models.JSONField(blank=True, default=dict)),
                ("last_summary", models.TextField(blank=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="mentor_memory",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Mentor Memory",
                "verbose_name_plural": "Mentor Memories",
            },
        ),
    ]
