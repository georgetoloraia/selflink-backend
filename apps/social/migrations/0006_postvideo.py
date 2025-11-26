from django.db import migrations, models
import django.db.models.deletion

import libs.idgen


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0005_postimage"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostVideo",
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
                ("file", models.FileField(upload_to="posts/videos/")),
                ("thumbnail", models.ImageField(blank=True, null=True, upload_to="posts/videos/thumbnails/")),
                ("duration_seconds", models.FloatField(blank=True, null=True)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("mime_type", models.CharField(default="video/mp4", max_length=64)),
                (
                    "post",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="video", to="social.post"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
