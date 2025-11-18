from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0003_commentimage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commentimage",
            name="image",
            field=models.ImageField(upload_to="posts/images/"),
        ),
    ]
