from __future__ import annotations

from django.conf import settings
from django.db import migrations, models

import libs.idgen


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
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
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("handle", models.CharField(max_length=30, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("bio", models.TextField(blank=True)),
                ("photo", models.URLField(blank=True)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("birth_time", models.TimeField(blank=True, null=True)),
                ("birth_place", models.CharField(blank=True, max_length=255)),
                ("locale", models.CharField(default="en-US", max_length=32)),
                ("flags", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["handle"], name="users_user_handle_idx"),
                    models.Index(fields=["email"], name="users_user_email_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="UserSettings",
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
                ("privacy", models.CharField(default="public", max_length=32)),
                ("dm_policy", models.CharField(default="everyone", max_length=32)),
                ("language", models.CharField(default="en", max_length=32)),
                ("quiet_hours", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="settings", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Block",
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
                    "target",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="blocked_by", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="blocks", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "unique_together": {("user", "target")},
            },
        ),
        migrations.CreateModel(
            name="Mute",
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
                    "target",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="muted_by", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="mutes", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "unique_together": {("user", "target")},
            },
        ),
        migrations.CreateModel(
            name="Device",
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
                ("push_token", models.CharField(max_length=255)),
                ("device_type", models.CharField(max_length=32)),
                ("last_seen", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="devices", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "unique_together": {("user", "push_token")},
            },
        ),
    ]
