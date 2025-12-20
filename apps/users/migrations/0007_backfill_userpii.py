from __future__ import annotations

from django.db import migrations


def backfill_user_pii(apps, schema_editor) -> None:
    User = apps.get_model("users", "User")
    UserPII = apps.get_model("users", "UserPII")

    for user in User.objects.all().iterator():
        UserPII.objects.update_or_create(
            user_id=user.id,
            defaults={
                "full_name": user.name or "",
                "email": user.email or "",
                "birth_date": user.birth_date,
                "birth_time": user.birth_time,
                "birth_place": user.birth_place or "",
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_rename_users_userp_email_8fda3f_idx_users_userp_email_4eeb07_idx"),
    ]

    operations = [
        migrations.RunPython(backfill_user_pii, migrations.RunPython.noop),
    ]

