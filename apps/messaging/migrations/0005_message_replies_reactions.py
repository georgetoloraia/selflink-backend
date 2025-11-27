from django.db import migrations, models
import django.db.models.deletion
import libs.idgen


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
        ("messaging", "0004_messageattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="reply_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replies",
                to="messaging.message",
            ),
        ),
        migrations.CreateModel(
            name="MessageReaction",
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
                ("emoji", models.CharField(max_length=16)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reactions",
                        to="messaging.message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_reactions",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
                "unique_together": {("message", "user", "emoji")},
            },
        ),
    ]
