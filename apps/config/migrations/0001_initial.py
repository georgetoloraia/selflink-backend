from __future__ import annotations

from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FeatureFlag",
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
                ("key", models.CharField(max_length=64, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("enabled", models.BooleanField(default=False)),
                ("rollout", models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
            ],
            options={
                "verbose_name": "Feature Flag",
                "verbose_name_plural": "Feature Flags",
            },
        ),
    ]
