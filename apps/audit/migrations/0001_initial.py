from __future__ import annotations

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("actor_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("action", models.CharField(max_length=128)),
                ("object_type", models.CharField(max_length=128)),
                ("object_id", models.CharField(max_length=128)),
                ("metadata", models.JSONField(default=dict, blank=True)),
                ("hash_prev", models.CharField(max_length=64, blank=True)),
                ("hash_self", models.CharField(max_length=64, blank=True, editable=False)),
                (
                    "actor_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["action", "created_at"], name="audit_audit_action_82fd8d_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["object_type", "object_id"], name="audit_audit_object__c9b0e7_idx"),
        ),
    ]
