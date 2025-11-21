from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profile", "0002_birth_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="birth_latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="birth_longitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="birth_timezone",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
