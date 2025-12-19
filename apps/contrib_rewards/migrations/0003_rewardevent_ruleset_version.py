from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contrib_rewards", "0002_ledgerentry"),
        ("contrib_rewards", "0002_rename_contrib_re_github__a562a7_idx_contrib_rew_github__30cabc_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="rewardevent",
            name="ruleset_version",
            field=models.CharField(default="v1", max_length=16),
        ),
    ]

