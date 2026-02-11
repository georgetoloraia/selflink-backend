from __future__ import annotations

import hashlib
import hmac
import json

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
    IPAY_WEBHOOK_SECRET="test_iph_secret",
    IPAY_SIGNATURE_HEADER="HTTP_X_IPAY_SIGNATURE",
    IPAY_PAID_STATUSES=["paid"],
    IPAY_FAILED_STATUSES=["failed"],
    IPAY_ALLOWED_CURRENCIES=["USD"],
)
class IpayWebhookTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="ipay@example.com",
            handle="ipay",
            name="iPay User",
            password="pass12345",
        )
        self.url = "/api/v1/payments/ipay/webhook/"

    def _create_checkout(self, amount_cents: int = 1500, currency: str = "USD") -> PaymentCheckout:
        return PaymentCheckout.objects.create(
            provider=PaymentEventProvider.IPAY,
            user=self.user,
            amount_cents=amount_cents,
            currency=currency,
        )

    def test_invalid_signature_rejected(self) -> None:
        checkout = self._create_checkout()
        payload = {
            "event_id": "ev_bad",
            "order_id": checkout.reference,
            "status": "paid",
            "amount": 1500,
            "currency": "USD",
        }
        body = json.dumps(payload).encode("utf-8")

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_IPAY_SIGNATURE="bad",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 0)

    def test_paid_event_mints_once(self) -> None:
        checkout = self._create_checkout()
        payload = {
            "event_id": "ev_paid",
            "order_id": checkout.reference,
            "status": "paid",
            "amount": 1500,
            "currency": "USD",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = _sign_payload("test_iph_secret", body)

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_IPAY_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 1)
        payment_event = PaymentEvent.objects.get(provider_event_id="ev_paid")
        self.assertIsNotNone(payment_event.verified_at)
        self.assertEqual(payment_event.amount_cents, 1500)
        self.assertEqual(payment_event.currency, "USD")
        account = get_or_create_user_account(self.user)
        self.assertEqual(get_balance_cents(account.account_key), 1500)

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_IPAY_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 1)
        self.assertEqual(get_balance_cents(account.account_key), 1500)

    def test_non_paid_event_does_not_mint(self) -> None:
        checkout = self._create_checkout()
        payload = {
            "event_id": "ev_pending",
            "order_id": checkout.reference,
            "status": "pending",
            "amount": 1500,
            "currency": "USD",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = _sign_payload("test_iph_secret", body)

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_IPAY_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 0)

    def test_amount_currency_mismatch_rejected(self) -> None:
        checkout = self._create_checkout(amount_cents=1000)
        payload = {
            "event_id": "ev_mismatch",
            "order_id": checkout.reference,
            "status": "paid",
            "amount": 2000,
            "currency": "USD",
        }
        body = json.dumps(payload).encode("utf-8")
        signature = _sign_payload("test_iph_secret", body)

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_IPAY_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEventType.MINT).count(), 0)
