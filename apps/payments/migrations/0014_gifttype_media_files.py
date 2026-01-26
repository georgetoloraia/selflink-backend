from __future__ import annotations

from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0013_seed_gift_effects"),
    ]

    operations = [
        migrations.AddField(
            model_name="gifttype",
            name="media_file",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="gifts/",
                validators=[FileExtensionValidator(["png"])],
                help_text="Upload a .png file (optional).",
            ),
        ),
        migrations.AddField(
            model_name="gifttype",
            name="animation_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="gifts/",
                validators=[FileExtensionValidator(["json"])],
                help_text="Upload a .json Lottie file (optional).",
            ),
        ),
    ]
