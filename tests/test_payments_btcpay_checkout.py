from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.payments.models import PaymentCheckout, PaymentEventProvider
from apps.users.models import User


@override_settings(
    FEATURE_FLAGS={"payments": True},
    BTCPAY_ALLOWED_CURRENCIES=["USD"],
)
class BtcPayCheckoutTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="btcpaybuyer@example.com",
            handle="btcpaybuyer",
            name="BTCPay Buyer",
            password="pass12345",
        )
        self.url = "/api/v1/payments/btcpay/checkout/"

    def test_requires_auth(self) -> None:
        response = self.client.post(self.url, data={"amount_cents": 100, "currency": "USD"})
        self.assertEqual(response.status_code, 401)

    @patch("apps.payments.btcpay.get_btcpay_client")
    def test_checkout_creates_payment_checkout_and_url(self, mock_get_client: Mock) -> None:
        mock_invoice = SimpleNamespace(invoice_id="inv_test_1", checkout_url="https://btcpay.example/i/inv_test_1")
        mock_client = Mock()
        mock_client.create_invoice.return_value = mock_invoice
        mock_get_client.return_value = mock_client

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data={"amount_cents": 1500, "currency": "USD"}, format="json")
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["amount_cents"], 1500)
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["payment_url"], "https://btcpay.example/i/inv_test_1")
        self.assertEqual(PaymentCheckout.objects.filter(provider=PaymentEventProvider.BTCPAY).count(), 1)

        checkout = PaymentCheckout.objects.get(provider=PaymentEventProvider.BTCPAY)
        self.assertEqual(checkout.provider_reference, "inv_test_1")
        mock_client.create_invoice.assert_called_once()
        called_kwargs = mock_client.create_invoice.call_args.kwargs
        self.assertEqual(called_kwargs["amount_cents"], 1500)
        self.assertEqual(called_kwargs["currency"], "USD")
        self.assertEqual(called_kwargs["reference"], checkout.reference)

    def test_currency_not_allowed(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data={"amount_cents": 1500, "currency": "GEL"}, format="json")
        self.assertEqual(response.status_code, 400)
