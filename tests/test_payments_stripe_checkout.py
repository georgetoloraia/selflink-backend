from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.payments.models import PaymentCheckout, PaymentEventProvider
from apps.users.models import User


@override_settings(
    FEATURE_FLAGS={"payments": True},
    STRIPE_ALLOWED_CURRENCIES=["USD"],
    STRIPE_CHECKOUT_MIN_CENTS=50,
    STRIPE_CHECKOUT_SUCCESS_URL="http://example.com/success",
    STRIPE_CHECKOUT_CANCEL_URL="http://example.com/cancel",
)
class StripeCheckoutTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="stripebuyer@example.com",
            handle="stripebuyer",
            name="Stripe Buyer",
            password="pass12345",
        )
        self.url = "/api/v1/payments/stripe/checkout/"

    def test_requires_auth(self) -> None:
        response = self.client.post(self.url, data={"amount_cents": 100, "currency": "USD"})
        self.assertEqual(response.status_code, 401)

    @patch("apps.payments.stripe_checkout.get_stripe_client")
    def test_checkout_creates_payment_checkout_and_url(self, mock_get_client: Mock) -> None:
        mock_session = Mock()
        mock_session.id = "cs_test_1"
        mock_session.url = "https://stripe.example/checkout"
        mock_client = Mock()
        mock_client.create_checkout_payment_session.return_value = mock_session
        mock_get_client.return_value = mock_client

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data={"amount_cents": 1500, "currency": "USD"}, format="json")
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["amount_cents"], 1500)
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["payment_url"], "https://stripe.example/checkout")
        self.assertEqual(PaymentCheckout.objects.filter(provider=PaymentEventProvider.STRIPE).count(), 1)

        checkout = PaymentCheckout.objects.get(provider=PaymentEventProvider.STRIPE)
        mock_client.create_checkout_payment_session.assert_called_once()
        called_kwargs = mock_client.create_checkout_payment_session.call_args.kwargs
        self.assertEqual(called_kwargs["amount_cents"], 1500)
        self.assertEqual(called_kwargs["currency"], "USD")
        self.assertEqual(called_kwargs["reference"], checkout.reference)
