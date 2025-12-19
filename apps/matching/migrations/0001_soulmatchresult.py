from __future__ import annotations

from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SoulMatchResult",
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
                ("pair_key", models.CharField(max_length=64)),
                ("rules_version", models.CharField(default="v1", max_length=32)),
                ("score", models.FloatField()),
                ("payload_json", models.JSONField(blank=True, default=dict)),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "unique_together": {("pair_key", "rules_version")},
                "indexes": [models.Index(fields=["pair_key", "rules_version"], name="matching_soul_pai_2847a3_idx")],
            },
        ),
    ]

