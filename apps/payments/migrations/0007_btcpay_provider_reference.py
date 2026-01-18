from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0006_payment_checkout_and_currency"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentevent",
            name="provider",
            field=models.CharField(
                choices=[("stripe", "Stripe"), ("ipay", "iPay"), ("btcpay", "BTCPay")],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="paymentcheckout",
            name="provider",
            field=models.CharField(
                choices=[("stripe", "Stripe"), ("ipay", "iPay"), ("btcpay", "BTCPay")],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="paymentcheckout",
            name="provider_reference",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
