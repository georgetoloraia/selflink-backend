from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.coin.models import CoinEvent
from apps.coin.services.ledger import get_balance_cents, get_or_create_user_account
from apps.payments.models import PaymentEvent
from apps.payments.providers.iap import VerificationResult
from apps.users.models import User


@override_settings(
    FEATURE_FLAGS={"payments": True},
    PAYMENTS_PROVIDER_ENABLED_IAP=True,
    IAP_SKU_MAP={"com.selflink.slc.499": {"amount_cents": 499, "currency": "USD"}},
)
class IapVerifyTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="iap@example.com",
            handle="iap",
            name="IAP User",
            password="pass12345",
        )
        self.url = "/api/v1/payments/iap/verify/"

    def test_unknown_sku_rejected(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            data={"platform": "ios", "product_id": "unknown", "transaction_id": "tx_1", "receipt": "r"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)

    def test_missing_receipt_rejected(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            data={"platform": "ios", "product_id": "com.selflink.slc.499", "transaction_id": "tx_1"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)

    def test_missing_purchase_token_rejected(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            data={"platform": "android", "product_id": "com.selflink.slc.499", "transaction_id": "order_1"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)

    @patch("apps.payments.iap.verify_apple_receipt")
    def test_successful_verification_mints_once(self, mock_verify: Mock) -> None:
        mock_verify.return_value = VerificationResult(
            ok=True,
            status="paid",
            provider_event_id="tx_paid",
            product_id="com.selflink.slc.499",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            data={
                "platform": "ios",
                "product_id": "com.selflink.slc.499",
                "transaction_id": "tx_paid",
                "receipt": "r",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 1)
        account = get_or_create_user_account(self.user)
        self.assertEqual(get_balance_cents(account.account_key), 499)

        response = self.client.post(
            self.url,
            data={
                "platform": "ios",
                "product_id": "com.selflink.slc.499",
                "transaction_id": "tx_paid",
                "receipt": "r",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 1)
        self.assertEqual(get_balance_cents(account.account_key), 499)

    @patch("apps.payments.iap.verify_apple_receipt")
    def test_verification_failure_does_not_mint(self, mock_verify: Mock) -> None:
        mock_verify.return_value = VerificationResult(
            ok=False,
            status="invalid",
            provider_event_id="tx_bad",
            product_id="com.selflink.slc.499",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            data={
                "platform": "ios",
                "product_id": "com.selflink.slc.499",
                "transaction_id": "tx_bad",
                "receipt": "r",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 0)
