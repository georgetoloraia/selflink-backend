from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0011_seed_test_gift"),
    ]

    operations = [
        migrations.AddField(
            model_name="gifttype",
            name="effects",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
