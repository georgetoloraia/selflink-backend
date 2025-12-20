from __future__ import annotations

from django.db import migrations, models


def add_birth_fields(apps, schema_editor) -> None:
    UserProfile = apps.get_model("profile", "UserProfile")
    table = UserProfile._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        existing = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(cursor, table)
        }

    field_names = [
        "birth_city",
        "birth_country",
        "birth_date",
        "birth_time",
        "birth_timezone",
        "birth_latitude",
        "birth_longitude",
    ]

    for field_name in field_names:
        field = UserProfile._meta.get_field(field_name)
        if field.column in existing:
            continue
        schema_editor.add_field(UserProfile, field)
        existing.add(field.column)


class Migration(migrations.Migration):

    dependencies = [
        ("profile", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_birth_fields, reverse_code=migrations.RunPython.noop)
            ],
            state_operations=[
                migrations.AddField(
                    model_name="userprofile",
                    name="birth_city",
                    field=models.CharField(blank=True, max_length=128),
                ),
                migrations.AddField(
                    model_name="userprofile",
                    name="birth_country",
                    field=models.CharField(blank=True, max_length=128),
                ),
                migrations.AddField(
                    model_name="userprofile",
                    name="birth_date",
                    field=models.DateField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="userprofile",
                    name="birth_latitude",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="userprofile",
                    name="birth_longitude",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="userprofile",
                    name="birth_time",
                    field=models.TimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="userprofile",
                    name="birth_timezone",
                    field=models.CharField(blank=True, max_length=64),
                ),
            ],
        ),
    ]
