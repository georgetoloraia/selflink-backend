from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="client_uuid",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("sent", "Sent"),
                    ("delivered", "Delivered"),
                    ("read", "Read"),
                ],
                default="sent",
                max_length=16,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="message",
            unique_together={("thread", "client_uuid")},
        ),
    ]
