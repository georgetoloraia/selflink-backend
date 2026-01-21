from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0008_payment_checkout_bog_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentevent",
            name="provider",
            field=models.CharField(
                choices=[
                    ("stripe", "Stripe"),
                    ("ipay", "iPay"),
                    ("btcpay", "BTCPay"),
                    ("apple_iap", "Apple IAP"),
                    ("google_iap", "Google IAP"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="paymentcheckout",
            name="provider",
            field=models.CharField(
                choices=[
                    ("stripe", "Stripe"),
                    ("ipay", "iPay"),
                    ("btcpay", "BTCPay"),
                    ("apple_iap", "Apple IAP"),
                    ("google_iap", "Google IAP"),
                ],
                max_length=32,
            ),
        ),
    ]
