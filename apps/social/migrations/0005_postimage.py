from __future__ import annotations

from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0004_alter_commentimage_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostImage",
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
                ("image", models.ImageField(upload_to="posts/images/")),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="images",
                        to="social.post",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "created_at"],
            },
        ),
    ]
