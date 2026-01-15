from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0004_payment_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentevent",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
