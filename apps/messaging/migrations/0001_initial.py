from __future__ import annotations

from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Thread",
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
                ("is_group", models.BooleanField(default=False)),
                ("title", models.CharField(blank=True, max_length=120)),
                (
                    "created_by",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="created_threads", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Message",
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
                ("body", models.TextField(blank=True)),
                (
                    "type",
                    models.CharField(
                        choices=[("text", "Text"), ("image", "Image"), ("system", "System")],
                        default="text",
                        max_length=16,
                    ),
                ),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "sender",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="sent_messages", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "thread",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="messages", to="messaging.thread"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="ThreadMember",
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
                (
                    "role",
                    models.CharField(
                        choices=[("member", "Member"), ("admin", "Admin")],
                        default="member",
                        max_length=16,
                    ),
                ),
                (
                    "last_read_message",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="readers", to="messaging.message"),
                ),
                (
                    "thread",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="members", to="messaging.thread"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="thread_memberships", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"unique_together": {("thread", "user")}},
        ),
    ]
