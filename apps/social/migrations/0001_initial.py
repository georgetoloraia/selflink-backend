from __future__ import annotations

from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("users", "0001_initial"),
        ("media", "0001_initial"),
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Post",
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
                ("text", models.TextField()),
                (
                    "visibility",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("followers", "Followers"),
                            ("private", "Private"),
                        ],
                        default="public",
                        max_length=16,
                    ),
                ),
                ("language", models.CharField(default="en", max_length=8)),
                ("like_count", models.PositiveIntegerField(default=0)),
                ("comment_count", models.PositiveIntegerField(default=0)),
                (
                    "author",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="posts", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Comment",
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
                ("text", models.TextField()),
                (
                    "author",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="comments", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "parent",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name="replies", to="social.comment"),
                ),
                (
                    "post",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="comments", to="social.post"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="Follow",
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
                    "followee",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="followers", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "follower",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="following", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"unique_together": {("follower", "followee")}},
        ),
        migrations.CreateModel(
            name="Gift",
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
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "gift_type",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, to="payments.gifttype"),
                ),
                (
                    "receiver",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="received_gifts", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "sender",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="sent_gifts", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Like",
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
                ("object_id", models.BigIntegerField()),
                (
                    "content_type",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, to="contenttypes.contenttype"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="likes", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"unique_together": {("user", "content_type", "object_id")}},
        ),
        migrations.CreateModel(
            name="Timeline",
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
                ("score", models.FloatField(default=0.0)),
                (
                    "post",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="timeline_entries", to="social.post"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="timeline_entries", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-score", "-created_at"], "unique_together": {("user", "post")}},
        ),
        migrations.AddField(
            model_name="post",
            name="media",
            field=models.ManyToManyField(blank=True, related_name="posts", to="media.mediaasset"),
        ),
    ]
