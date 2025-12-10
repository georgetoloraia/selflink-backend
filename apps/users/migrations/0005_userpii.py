from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_personalmapprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPII",
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
                ("full_name", models.CharField(blank=True, max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone_number", models.CharField(blank=True, max_length=32)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("birth_time", models.TimeField(blank=True, null=True)),
                ("birth_place", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pii",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["email"], name="users_userp_email_8fda3f_idx")],
            },
        ),
    ]
