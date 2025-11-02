from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersettings",
            name="push_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="usersettings",
            name="email_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="usersettings",
            name="digest_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
