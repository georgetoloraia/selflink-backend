from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0014_gifttype_media_files"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gifttype",
            name="art_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="gifttype",
            name="media_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="gifttype",
            name="animation_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
