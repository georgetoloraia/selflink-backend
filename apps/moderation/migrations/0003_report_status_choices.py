from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="report",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("in_review", "In Review"),
                    ("resolved", "Resolved"),
                    ("dismissed", "Dismissed"),
                ],
                default="open",
                max_length=32,
            ),
        ),
    ]
