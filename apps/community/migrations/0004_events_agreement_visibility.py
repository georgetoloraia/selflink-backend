from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from libs.idgen import generate_id


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0003_problem_agreement_license_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="views_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="problem",
            name="last_activity_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.CreateModel(
            name="ProblemEvent",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        primary_key=True, serialize=False, editable=False, default=generate_id
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("type", models.CharField(max_length=64, db_index=True)),
                ("metadata", models.JSONField(default=dict, blank=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="community_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "problem",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="community.problem",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="problemevent",
            index=models.Index(fields=["problem", "-created_at"], name="community_p_prob_id_e6ab7b_idx"),
        ),
        migrations.AddIndex(
            model_name="problemevent",
            index=models.Index(fields=["type", "-created_at"], name="community_p_type_7f6b26_idx"),
        ),
    ]
