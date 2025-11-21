from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profile", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="birth_city",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="birth_country",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="birth_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="birth_latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="birth_longitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="birth_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="birth_timezone",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
