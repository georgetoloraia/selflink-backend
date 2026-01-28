from __future__ import annotations

import hashlib
from unittest.mock import patch

import pytest
from django.test.utils import capture_on_commit_callbacks
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.coin.services.ledger import mint_for_payment
from apps.payments.models import GiftType, PaymentEvent
from apps.social.models import Comment, Post
from apps.users.models import User


def _mint_slc(user: User, amount_cents: int, provider_event_id: str) -> None:
    event = PaymentEvent.objects.create(
        provider=PaymentEvent.Provider.STRIPE,
        provider_event_id=provider_event_id,
        event_type="checkout.session.completed",
        user=user,
        amount_cents=amount_cents,
        status=PaymentEvent.Status.RECEIVED,
        raw_body_hash=hashlib.sha256(provider_event_id.encode("utf-8")).hexdigest(),
        verified_at=timezone.now(),
    )
    mint_for_payment(payment_event=event)


@pytest.mark.django_db(transaction=True)
def test_gift_publish_event_payload_post() -> None:
    sender = User.objects.create_user(email="rt1@example.com", password="pass1234", handle="rt1", name="RT One")
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="rt_heart",
        name="RT Heart",
        price_cents=100,
        price_slc_cents=100,
        is_active=True,
        media_url="/media/gifts/test-heart.png",
    )
    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_rt_1")

    client = APIClient()
    client.force_authenticate(user=sender)

    with patch("apps.social.events.publish_realtime_event") as mocked_publish:
        with capture_on_commit_callbacks(execute=True):
            response = client.post(
                f"/api/v1/posts/{post.id}/gifts/",
                data={"gift_type_id": gift_type.id, "quantity": 1},
                format="json",
                HTTP_IDEMPOTENCY_KEY="8c1d6c8d-4a35-4f5a-9d6e-6c5c5f0a6f1a",
            )
        assert response.status_code == 201
        assert mocked_publish.call_count == 1
        channel, payload = mocked_publish.call_args[0]
        assert channel == f"post:{post.id}"
        assert payload["type"] == "gift.received"
        assert payload["target"]["type"] == "post"
        assert payload["target"]["id"] == post.id
        assert payload["sender"]["id"] == sender.id
        assert payload["gift_type"]["id"] == gift_type.id
        assert payload["gift_type"]["key"] == gift_type.key
        assert "effects" in payload["gift_type"]
        assert payload["gift_type"]["effects"].get("version") == 2
        assert "server_time" in payload
        assert "expires_at" in payload
        assert payload["quantity"] == 1
        assert payload["total_amount_cents"] == 100


@pytest.mark.django_db(transaction=True)
def test_gift_publish_event_payload_comment() -> None:
    sender = User.objects.create_user(email="rt3@example.com", password="pass1234", handle="rt3", name="RT Three")
    post = Post.objects.create(author=sender, text="hello")
    comment = Comment.objects.create(author=sender, post=post, text="hi")
    gift_type = GiftType.objects.create(
        key="rt_comment",
        name="RT Comment Gift",
        price_cents=200,
        price_slc_cents=200,
        is_active=True,
    )
    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_rt_3")

    client = APIClient()
    client.force_authenticate(user=sender)

    with patch("apps.social.events.publish_realtime_event") as mocked_publish:
        with capture_on_commit_callbacks(execute=True):
            response = client.post(
                f"/api/v1/comments/{comment.id}/gifts/",
                data={"gift_type_id": gift_type.id, "quantity": 1},
                format="json",
                HTTP_IDEMPOTENCY_KEY="6c9e2a5a-1b63-4e3e-8a7f-4d3d4b6a9a1b",
            )
        assert response.status_code == 201
        assert mocked_publish.call_count == 1
        channel, payload = mocked_publish.call_args[0]
        assert channel == f"comment:{comment.id}"
        assert payload["type"] == "gift.received"
        assert payload["target"]["type"] == "comment"
        assert payload["target"]["id"] == comment.id
        assert payload["gift_type"]["id"] == gift_type.id
        assert "effects" in payload["gift_type"]
        assert payload["gift_type"]["effects"].get("version") == 2
        assert "server_time" in payload
        assert "expires_at" in payload


@pytest.mark.django_db(transaction=True)
def test_gift_publish_failure_does_not_block() -> None:
    sender = User.objects.create_user(email="rt2@example.com", password="pass1234", handle="rt2", name="RT Two")
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="rt_star",
        name="RT Star",
        price_cents=100,
        price_slc_cents=100,
        is_active=True,
    )
    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_rt_2")

    client = APIClient()
    client.force_authenticate(user=sender)

    with patch("apps.social.events.publish_realtime_event", side_effect=Exception("boom")):
        with capture_on_commit_callbacks(execute=True):
            response = client.post(
                f"/api/v1/posts/{post.id}/gifts/",
                data={"gift_type_id": gift_type.id, "quantity": 1},
                format="json",
                HTTP_IDEMPOTENCY_KEY="9f5d2f7b-7e2f-4e1a-8f7f-2d0f0d1b2a3c",
            )
        assert response.status_code == 201


@pytest.mark.django_db
@override_settings(PUBLIC_BASE_URL="https://api.example.com")
def test_gift_publish_without_request_context() -> None:
    sender = User.objects.create_user(email="rt4@example.com", password="pass1234", handle="rt4", name="RT Four")
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="rt_noctx",
        name="RT NoCtx",
        price_cents=100,
        price_slc_cents=100,
        is_active=True,
        media_url="/media/gifts/test-heart.png",
    )
    from apps.social.models import PaidReaction
    from apps.coin.services.ledger import create_spend

    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_rt_4")
    coin_event = create_spend(
        user=sender,
        amount_cents=100,
        reference="gift:post:test",
        note="test",
    )
    reaction = PaidReaction.objects.create(
        sender=sender,
        target_type=PaidReaction.TargetType.POST,
        post=post,
        gift_type=gift_type,
        quantity=1,
        total_amount_cents=100,
        coin_event=coin_event,
    )
    from apps.social.events import publish_gift_received

    with patch("apps.social.events.publish_realtime_event") as mocked_publish:
        publish_gift_received(reaction=reaction, channel=f"post:{post.id}", request=None)
        assert mocked_publish.call_count == 1
        _, payload = mocked_publish.call_args[0]
        assert payload["gift_type"]["media_url"] == "https://api.example.com/media/gifts/test-heart.png"
        assert "effects" in payload["gift_type"]
