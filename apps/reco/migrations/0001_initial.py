from __future__ import annotations

from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SoulMatchProfile",
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
                ("life_path", models.CharField(blank=True, max_length=32)),
                ("avg_sentiment", models.FloatField(default=0.0)),
                ("social_score", models.FloatField(default=0.0)),
                ("traits", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="soulmatch_profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "SoulMatch Profile",
                "verbose_name_plural": "SoulMatch Profiles",
            },
        ),
        migrations.CreateModel(
            name="SoulMatchScore",
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
                ("score", models.FloatField()),
                ("breakdown", models.JSONField(blank=True, default=dict)),
                (
                    "target",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="matched_by", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="soulmatches", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "SoulMatch Score",
                "verbose_name_plural": "SoulMatch Scores",
                "unique_together": {("user", "target")},
            },
        ),
    ]
