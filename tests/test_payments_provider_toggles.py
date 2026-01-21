from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.users.models import User


@override_settings(
    FEATURE_FLAGS={"payments": True},
    PAYMENTS_PROVIDER_ENABLED_STRIPE=False,
    PAYMENTS_PROVIDER_ENABLED_IPAY=False,
    PAYMENTS_PROVIDER_ENABLED_BTCPAY=False,
    PAYMENTS_PROVIDER_ENABLED_IAP=False,
)
class PaymentProviderToggleTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="toggle@example.com",
            handle="toggle",
            name="Toggle User",
            password="pass12345",
        )

    def test_stripe_disabled_blocks_checkout(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/payments/stripe/checkout/", data={"amount_cents": 100, "currency": "USD"})
        self.assertEqual(response.status_code, 403)

    def test_stripe_disabled_blocks_webhook(self) -> None:
        response = self.client.post(
            "/api/v1/payments/stripe/webhook/",
            data=b"{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_ipay_disabled_blocks_checkout(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/payments/ipay/checkout/", data={"amount_cents": 100, "currency": "USD"})
        self.assertEqual(response.status_code, 403)

    def test_ipay_disabled_blocks_webhook(self) -> None:
        response = self.client.post(
            "/api/v1/payments/ipay/webhook/",
            data=b"{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_btcpay_disabled_blocks_checkout(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/payments/btcpay/checkout/", data={"amount_cents": 100, "currency": "USD"})
        self.assertEqual(response.status_code, 403)

    def test_btcpay_disabled_blocks_webhook(self) -> None:
        response = self.client.post(
            "/api/v1/payments/btcpay/webhook/",
            data=b"{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_iap_disabled_blocks_verify(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/payments/iap/verify/",
            data={"platform": "ios", "product_id": "com.selflink.slc.499", "transaction_id": "tx", "receipt": "r"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
