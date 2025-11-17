from __future__ import annotations

from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="text",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.CreateModel(
            name="CommentImage",
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
                ("image", models.ImageField(upload_to="comment_images/")),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="images",
                        to="social.comment",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "created_at"],
            },
        ),
    ]
