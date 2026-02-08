from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from libs.idgen import generate_id


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="status",
            field=models.CharField(default="open", max_length=32, db_index=True),
        ),
        migrations.CreateModel(
            name="ProblemLike",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        primary_key=True, serialize=False, editable=False, default=generate_id
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "problem",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="community.problem",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="problem_likes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("problem", "user")},
            },
        ),
        migrations.CreateModel(
            name="ProblemCommentLike",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        primary_key=True, serialize=False, editable=False, default=generate_id
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="community.problemcomment",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="problem_comment_likes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("comment", "user")},
            },
        ),
    ]
