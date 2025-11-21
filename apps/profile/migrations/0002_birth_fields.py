from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profile", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
ALTER TABLE profile_userprofile
    ADD COLUMN IF NOT EXISTS birth_city varchar(128) DEFAULT '' NOT NULL,
    ADD COLUMN IF NOT EXISTS birth_country varchar(128) DEFAULT '' NOT NULL,
    ADD COLUMN IF NOT EXISTS birth_date date,
    ADD COLUMN IF NOT EXISTS birth_time time,
    ADD COLUMN IF NOT EXISTS birth_timezone varchar(64) DEFAULT '' NOT NULL,
    ADD COLUMN IF NOT EXISTS birth_latitude double precision,
    ADD COLUMN IF NOT EXISTS birth_longitude double precision;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
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
