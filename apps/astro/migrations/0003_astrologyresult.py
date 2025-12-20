from __future__ import annotations

from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("astro", "0002_rename_apps_astro_u_user_id_8a558b_idx_astro_birth_user_id_f706c3_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AstrologyResult",
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
                ("birth_data_hash", models.CharField(max_length=64)),
                ("rules_version", models.CharField(default="v1", max_length=32)),
                ("payload_json", models.JSONField()),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "unique_together": {("birth_data_hash", "rules_version")},
                "indexes": [
                    models.Index(
                        fields=["birth_data_hash", "rules_version"],
                        name="astro_astro_birth_d_6b5a2f_idx",
                    )
                ],
            },
        ),
    ]

