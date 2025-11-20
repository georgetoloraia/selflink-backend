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
            name="UserProfile",
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
                ("gender", models.CharField(blank=True, choices=[("male", "male"), ("female", "female"), ("non_binary", "non_binary"), ("other", "other"), ("prefer_not_to_say", "prefer_not_to_say")], max_length=16)),
                ("orientation", models.CharField(blank=True, choices=[("hetero", "hetero"), ("homo", "homo"), ("bi", "bi"), ("pan", "pan"), ("asexual", "asexual"), ("other", "other"), ("prefer_not_to_say", "prefer_not_to_say")], max_length=32)),
                ("relationship_goal", models.CharField(choices=[("casual", "casual"), ("long_term", "long_term"), ("marriage", "marriage"), ("unsure", "unsure")], default="unsure", max_length=32)),
                ("values", models.JSONField(blank=True, default=list)),
                ("preferred_lifestyle", models.JSONField(blank=True, default=list)),
                ("attachment_style", models.CharField(blank=True, choices=[("secure", "secure"), ("anxious", "anxious"), ("avoidant", "avoidant"), ("mixed", "mixed")], max_length=32)),
                ("love_language", models.JSONField(blank=True, default=list)),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user"], name="profile_user_id_idx"),
                ],
            },
        ),
    ]
