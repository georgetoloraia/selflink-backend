from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("coin", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coinaccount",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="coin_account",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
