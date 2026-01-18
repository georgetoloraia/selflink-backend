from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.coin.models import CoinEvent
from apps.coin.services.ledger import get_balance_cents, get_or_create_user_account
from apps.payments.models import PaymentCheckout, PaymentEvent
from apps.users.models import User


@override_settings(FEATURE_FLAGS={"payments": True})
class StripeWebhookCoinTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="coinbuyer@example.com",
            handle="coinbuyer",
            name="Coin Buyer",
            password="pass12345",
        )
        self.url = "/api/v1/payments/stripe/webhook/"

    @patch("apps.payments.webhook.get_stripe_client")
    def test_duplicate_webhook_does_not_double_mint(self, mock_get_client: Mock) -> None:
        checkout = PaymentCheckout.objects.create(
            provider=PaymentEvent.Provider.STRIPE,
            user=self.user,
            amount_cents=1500,
            currency="USD",
        )
        event = {
            "id": "evt_coin_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": checkout.reference,
                    "amount_total": 1500,
                    "currency": "USD",
                    "payment_status": "paid",
                }
            },
        }
        mock_client = Mock()
        mock_client.construct_event.return_value = event
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=valid",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 1)
        account = get_or_create_user_account(self.user)
        self.assertEqual(get_balance_cents(account.account_key), 1500)
        payment_event = PaymentEvent.objects.get(
            provider=PaymentEvent.Provider.STRIPE,
            provider_event_id="evt_coin_1",
        )
        self.assertEqual(payment_event.amount_cents, 1500)

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=valid",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 1)
        self.assertEqual(get_balance_cents(account.account_key), 1500)

        self.assertIsNotNone(payment_event.minted_coin_event_id)

    @patch("apps.payments.webhook.get_stripe_client")
    def test_invalid_signature_rejected(self, mock_get_client: Mock) -> None:
        mock_client = Mock()
        mock_client.construct_event.side_effect = Exception("invalid signature")
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=invalid",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)

    @patch("apps.payments.webhook.get_stripe_client")
    def test_non_paid_event_does_not_mint(self, mock_get_client: Mock) -> None:
        checkout = PaymentCheckout.objects.create(
            provider=PaymentEvent.Provider.STRIPE,
            user=self.user,
            amount_cents=1500,
            currency="USD",
        )
        event = {
            "id": "evt_coin_2",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": checkout.reference,
                    "amount_total": 1500,
                    "currency": "USD",
                    "payment_status": "unpaid",
                }
            },
        }
        mock_client = Mock()
        mock_client.construct_event.return_value = event
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=valid",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 0)

    @patch("apps.payments.webhook.get_stripe_client")
    def test_unknown_reference_rejected(self, mock_get_client: Mock) -> None:
        event = {
            "id": "evt_coin_3",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": "missing",
                    "amount_total": 1500,
                    "currency": "USD",
                    "payment_status": "paid",
                }
            },
        }
        mock_client = Mock()
        mock_client.construct_event.return_value = event
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=valid",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 0)

    @patch("apps.payments.webhook.get_stripe_client")
    def test_payment_event_user_mismatch_rejected(self, mock_get_client: Mock) -> None:
        other = User.objects.create_user(
            email="other@example.com",
            handle="other",
            name="Other",
            password="pass12345",
        )
        checkout = PaymentCheckout.objects.create(
            provider=PaymentEvent.Provider.STRIPE,
            user=self.user,
            amount_cents=1500,
            currency="USD",
        )
        PaymentEvent.objects.create(
            provider=PaymentEvent.Provider.STRIPE,
            provider_event_id="evt_coin_4",
            event_type="checkout.session.completed",
            user=other,
            amount_cents=1500,
            currency="USD",
            status=PaymentEvent.Status.RECEIVED,
            raw_body_hash="hash",
        )
        event = {
            "id": "evt_coin_4",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": checkout.reference,
                    "amount_total": 1500,
                    "currency": "USD",
                    "payment_status": "paid",
                }
            },
        }
        mock_client = Mock()
        mock_client.construct_event.return_value = event
        mock_get_client.return_value = mock_client

        response = self.client.post(
            self.url,
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=valid",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT).count(), 0)
