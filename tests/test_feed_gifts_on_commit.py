from __future__ import annotations

import hashlib
from unittest.mock import patch

from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.coin.services.ledger import mint_for_payment
from apps.payments.models import GiftType, PaymentEvent
from apps.social.models import Post
from apps.users.models import User


class GiftPublishOnCommitTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.sender = User.objects.create_user(
            email="commit@example.com",
            password="pass1234",
            handle="commit",
            name="Commit User",
        )
        self.post = Post.objects.create(author=self.sender, text="hello")
        self.gift_type = GiftType.objects.create(
            key="commit_gift",
            name="Commit Gift",
            price_cents=100,
            price_slc_cents=100,
            is_active=True,
        )
        event = PaymentEvent.objects.create(
            provider=PaymentEvent.Provider.STRIPE,
            provider_event_id="evt_commit_1",
            event_type="checkout.session.completed",
            user=self.sender,
            amount_cents=1000,
            status=PaymentEvent.Status.RECEIVED,
            raw_body_hash=hashlib.sha256(b"evt_commit_1").hexdigest(),
            verified_at=timezone.now(),
        )
        mint_for_payment(payment_event=event)
        self.client = APIClient()
        self.client.force_authenticate(user=self.sender)

    def test_publish_only_after_commit(self) -> None:
        with patch("apps.social.events.publish_realtime_event") as mocked_publish:
            with transaction.atomic():
                response = self.client.post(
                    f"/api/v1/posts/{self.post.id}/gifts/",
                    data={"gift_type_id": self.gift_type.id, "quantity": 1},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY="a6b1d0a4-3c9e-4b74-9f1a-4b785a6d9d01",
                )
                self.assertEqual(response.status_code, 201)
                self.assertEqual(mocked_publish.call_count, 0)
            self.assertEqual(mocked_publish.call_count, 1)

    def test_publish_not_called_on_rollback(self) -> None:
        with patch("apps.social.events.publish_realtime_event") as mocked_publish:
            try:
                with transaction.atomic():
                    self.client.post(
                        f"/api/v1/posts/{self.post.id}/gifts/",
                        data={"gift_type_id": self.gift_type.id, "quantity": 1},
                        format="json",
                        HTTP_IDEMPOTENCY_KEY="d4e1f5d6-6d0c-4fcb-9b49-7e0e2b5f3f5f",
                    )
                    raise RuntimeError("force rollback")
            except RuntimeError:
                pass
            self.assertEqual(mocked_publish.call_count, 0)
