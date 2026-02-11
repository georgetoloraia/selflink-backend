from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.coin.models import CoinEvent, CoinEventType
from apps.coin.services.ledger import get_balance_cents, get_or_create_user_account
from apps.payments.models import PaymentCheckout, PaymentEvent, PaymentEventProvider
from apps.users.models import User


def _sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


@override_settings(
    FEATURE_FLAGS={"payments": True},
    BTCPAY_WEBHOOK_SECRET="test_btcpay_secret",
    BTCPAY_SIGNATURE_HEADER="HTTP_BTCPAY_SIG",
    BTCPAY_ALLOWED_CURRENCIES=["USD"],
    BTCPAY_PAID_STATUSES=["settled"],
    BTCPAY_FAILED_STATUSES=["expired"],
)
class BtcPayWebhookTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="btcpay@example.com",
            handle="btcpay",
            name="BTCPay User",
            password="pass12345",
        )
        self.url = "/api/v1/payments/btcpay/webhook/"

    def _create_checkout(self, invoice_id: str, amount_cents: int = 1500, currency: str = "USD") -> PaymentCheckout:
        return PaymentCheckout.objects.create(
            provider=PaymentEventProvider.BTCPAY,
            user=self.user,
            amount_cents=amount_cents,
            currency=currency,
            provider_reference=invoice_id,
        )

    def test_invalid_signature_rejected(self) -> None:
        body = json.dumps({"invoiceId": "inv_bad", "type": "InvoiceSettled"}).encode("utf-8")
        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_BTCPAY_SIG="bad",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 0)

    @patch("apps.payments.webhooks.btcpay_webhook.get_btcpay_client")
    def test_paid_event_mints_once(self, mock_get_client: Mock) -> None:
        checkout = self._create_checkout(invoice_id="inv_paid")
        body = json.dumps({"invoiceId": "inv_paid", "type": "InvoiceSettled"}).encode("utf-8")
        signature = _sign_payload("test_btcpay_secret", body)

        invoice_payload = {
            "id": "inv_paid",
            "amount": "15.00",
            "currency": "USD",
            "status": "settled",
            "metadata": {"reference": checkout.reference},
        }
        mock_client = Mock()
        mock_client.get_invoice.return_value = invoice_payload
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_BTCPAY_SIG=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 1)
        payment_event = PaymentEvent.objects.get(provider_event_id="inv_paid")
        self.assertIsNotNone(payment_event.verified_at)
        self.assertEqual(payment_event.amount_cents, 1500)
        self.assertEqual(payment_event.currency, "USD")
        account = get_or_create_user_account(self.user)
        self.assertEqual(get_balance_cents(account.account_key), 1500)

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_BTCPAY_SIG=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 1)
        self.assertEqual(get_balance_cents(account.account_key), 1500)

    @patch("apps.payments.webhooks.btcpay_webhook.get_btcpay_client")
    def test_non_final_event_does_not_mint(self, mock_get_client: Mock) -> None:
        checkout = self._create_checkout(invoice_id="inv_pending")
        body = json.dumps({"invoiceId": "inv_pending", "type": "InvoiceProcessing"}).encode("utf-8")
        signature = _sign_payload("test_btcpay_secret", body)

        invoice_payload = {
            "id": "inv_pending",
            "amount": "15.00",
            "currency": "USD",
            "status": "processing",
            "metadata": {"reference": checkout.reference},
        }
        mock_client = Mock()
        mock_client.get_invoice.return_value = invoice_payload
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_BTCPAY_SIG=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 0)

    @patch("apps.payments.webhooks.btcpay_webhook.get_btcpay_client")
    def test_amount_currency_mismatch_rejected(self, mock_get_client: Mock) -> None:
        checkout = self._create_checkout(invoice_id="inv_mismatch", amount_cents=1000)
        body = json.dumps({"invoiceId": "inv_mismatch", "type": "InvoiceSettled"}).encode("utf-8")
        signature = _sign_payload("test_btcpay_secret", body)

        invoice_payload = {
            "id": "inv_mismatch",
            "amount": "20.00",
            "currency": "USD",
            "status": "settled",
            "metadata": {"reference": checkout.reference},
        }
        mock_client = Mock()
        mock_client.get_invoice.return_value = invoice_payload
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_BTCPAY_SIG=signature,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 0)

    @patch("apps.payments.webhooks.btcpay_webhook.get_btcpay_client")
    def test_unknown_reference_rejected(self, mock_get_client: Mock) -> None:
        body = json.dumps({"invoiceId": "inv_missing", "type": "InvoiceSettled"}).encode("utf-8")
        signature = _sign_payload("test_btcpay_secret", body)

        invoice_payload = {
            "id": "inv_missing",
            "amount": "15.00",
            "currency": "USD",
            "status": "settled",
            "metadata": {"reference": "missing"},
        }
        mock_client = Mock()
        mock_client.get_invoice.return_value = invoice_payload
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_BTCPAY_SIG=signature,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 0)
