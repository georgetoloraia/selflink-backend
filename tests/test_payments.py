from django.test import TestCase

from apps.payments.models import Subscription, Wallet
from apps.payments.services import map_stripe_status
from apps.users.models import User


class PaymentsTests(TestCase):
    def test_map_stripe_status(self):
        self.assertEqual(map_stripe_status("active"), Subscription.Status.ACTIVE)
        self.assertEqual(map_stripe_status("past_due"), Subscription.Status.PAST_DUE)
        self.assertEqual(map_stripe_status("unknown"), Subscription.Status.INCOMPLETE)

    def test_wallet_external_customer(self):
        user = User.objects.create_user(email="wallet@example.com", handle="wallet", name="Wallet", password="pass12345")
        wallet, _ = Wallet.objects.get_or_create(user=user)
        self.assertIsNone(wallet.external_customer_id or None)
