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
            name="BirthData",
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
                ("date_of_birth", models.DateField()),
                ("time_of_birth", models.TimeField()),
                ("timezone", models.CharField(max_length=64)),
                ("city", models.CharField(blank=True, max_length=128)),
                ("country", models.CharField(blank=True, max_length=128)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="birth_data", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user"], name="apps_astro_u_user_id_8a558b_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="NatalChart",
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
                ("planets", models.JSONField()),
                ("houses", models.JSONField()),
                ("aspects", models.JSONField(blank=True, default=dict)),
                ("calculated_at", models.DateTimeField(auto_now_add=True)),
                (
                    "birth_data",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="natal_chart", to="astro.birthdata"),
                ),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="natal_chart", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user"], name="apps_astro_u_user_id_2d8ad8_idx"),
                ],
            },
        ),
    ]
