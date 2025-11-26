from __future__ import annotations

from django.db import migrations, models
import libs.idgen


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0003_message_delivery_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageAttachment",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        default=libs.idgen.generate_id, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("file", models.FileField(upload_to="messages/attachments/")),
                (
                    "type",
                    models.CharField(
                        choices=[("image", "Image"), ("video", "Video")],
                        max_length=8,
                    ),
                ),
                ("mime_type", models.CharField(max_length=128)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("duration_seconds", models.FloatField(blank=True, null=True)),
                (
                    "message",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="attachments", to="messaging.message"),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
