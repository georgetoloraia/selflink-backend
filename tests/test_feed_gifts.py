from __future__ import annotations

import hashlib

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.coin.models import CoinEvent, CoinEventType
from apps.coin.services.ledger import mint_for_payment
from apps.payments.models import GiftType, PaymentEvent, PaymentEventProvider, PaymentEventStatus
from apps.social.models import Comment, PaidReaction, Post
from apps.users.models import User


def _mint_slc(user: User, amount_cents: int, provider_event_id: str) -> None:
    event = PaymentEvent.objects.create(
        provider=PaymentEventProvider.STRIPE,
        provider_event_id=provider_event_id,
        event_type="checkout.session.completed",
        user=user,
        amount_cents=amount_cents,
        status=PaymentEventStatus.RECEIVED,
        raw_body_hash=hashlib.sha256(provider_event_id.encode("utf-8")).hexdigest(),
        verified_at=timezone.now(),
    )
    mint_for_payment(payment_event=event)


@pytest.mark.django_db
def test_post_gift_idempotency_same_payload() -> None:
    sender = User.objects.create_user(
        email="gift1@example.com", password="pass1234", handle="gift1", name="Gift One"
    )
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="rose",
        name="Rose",
        price_cents=100,
        price_slc_cents=100,
        is_active=True,
    )
    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_gift_1")

    client = APIClient()
    client.force_authenticate(user=sender)
    headers = {"HTTP_IDEMPOTENCY_KEY": "2f5d2c2d-3a9a-4b7d-9f68-ef2df3e3f6f6"}
    payload = {"gift_type_id": gift_type.id, "quantity": 2}

    response = client.post(f"/api/v1/posts/{post.id}/gifts/", data=payload, format="json", **headers)
    assert response.status_code == 201
    spend_count = CoinEvent.objects.filter(event_type=CoinEventType.SPEND).count()

    response_repeat = client.post(f"/api/v1/posts/{post.id}/gifts/", data=payload, format="json", **headers)
    assert response_repeat.status_code == 200
    assert CoinEvent.objects.filter(event_type=CoinEventType.SPEND).count() == spend_count


@pytest.mark.django_db
def test_post_gift_idempotency_conflict_returns_400() -> None:
    sender = User.objects.create_user(
        email="gift2@example.com", password="pass1234", handle="gift2", name="Gift Two"
    )
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="spark",
        name="Spark",
        price_cents=100,
        price_slc_cents=100,
        is_active=True,
    )
    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_gift_2")

    client = APIClient()
    client.force_authenticate(user=sender)
    headers = {"HTTP_IDEMPOTENCY_KEY": "9a6c5e3f-30b0-4c2c-8c32-1d4b1ddcde98"}

    response = client.post(
        f"/api/v1/posts/{post.id}/gifts/",
        data={"gift_type_id": gift_type.id, "quantity": 1},
        format="json",
        **headers,
    )
    assert response.status_code == 201

    conflict = client.post(
        f"/api/v1/posts/{post.id}/gifts/",
        data={"gift_type_id": gift_type.id, "quantity": 2},
        format="json",
        **headers,
    )
    assert conflict.status_code == 400
    assert conflict.data.get("code") == "idempotency_conflict"


@pytest.mark.django_db
def test_comment_gift_inactive_rejected() -> None:
    sender = User.objects.create_user(
        email="gift3@example.com", password="pass1234", handle="gift3", name="Gift Three"
    )
    post = Post.objects.create(author=sender, text="hello")
    comment = Comment.objects.create(post=post, author=sender, text="hi")
    gift_type = GiftType.objects.create(
        key="fire",
        name="Fire",
        price_cents=100,
        price_slc_cents=100,
        is_active=False,
    )

    client = APIClient()
    client.force_authenticate(user=sender)
    headers = {"HTTP_IDEMPOTENCY_KEY": "b2d35f48-3ae7-4b3a-ae0a-5f6e3f4e0c0d"}
    response = client.post(
        f"/api/v1/comments/{comment.id}/gifts/",
        data={"gift_type_id": gift_type.id, "quantity": 1},
        format="json",
        **headers,
    )
    assert response.status_code == 400
    assert response.data.get("code") == "gift_inactive"


@pytest.mark.django_db
def test_gift_spend_records_reference_metadata() -> None:
    sender = User.objects.create_user(
        email="gift4@example.com", password="pass1234", handle="gift4", name="Gift Four"
    )
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="star",
        name="Star",
        price_cents=250,
        price_slc_cents=250,
        is_active=True,
    )
    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_gift_4")

    client = APIClient()
    client.force_authenticate(user=sender)
    headers = {"HTTP_IDEMPOTENCY_KEY": "c3e8b7b6-74a8-4ccf-86d7-4f9e2f0a3a2c"}
    response = client.post(
        f"/api/v1/posts/{post.id}/gifts/",
        data={"gift_type_id": gift_type.id, "quantity": 1},
        format="json",
        **headers,
    )
    assert response.status_code == 201
    reaction = PaidReaction.objects.get(id=response.data["reaction"]["id"])
    assert reaction.coin_event.metadata.get("reference") == f"gift:post:{post.id}:{gift_type.key}"
    gift_payload = response.data["reaction"]["gift_type"]
    assert "effects" in gift_payload


@pytest.mark.django_db
def test_gift_insufficient_funds_returns_code() -> None:
    sender = User.objects.create_user(
        email="gift5@example.com", password="pass1234", handle="gift5", name="Gift Five"
    )
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="moon",
        name="Moon",
        price_cents=100,
        price_slc_cents=100,
        is_active=True,
    )

    client = APIClient()
    client.force_authenticate(user=sender)
    headers = {"HTTP_IDEMPOTENCY_KEY": "d8f12e60-8a3b-4c3f-9d62-6a9ad1e2b1a1"}
    response = client.post(
        f"/api/v1/posts/{post.id}/gifts/",
        data={"gift_type_id": gift_type.id, "quantity": 1},
        format="json",
        **headers,
    )
    assert response.status_code == 400
    assert response.data.get("code") == "insufficient_funds"


@pytest.mark.django_db
def test_gift_requires_idempotency_key() -> None:
    sender = User.objects.create_user(
        email="gift6@example.com", password="pass1234", handle="gift6", name="Gift Six"
    )
    post = Post.objects.create(author=sender, text="hello")
    gift_type = GiftType.objects.create(
        key="sun",
        name="Sun",
        price_cents=100,
        price_slc_cents=100,
        is_active=True,
    )
    _mint_slc(sender, amount_cents=1000, provider_event_id="evt_gift_6")

    client = APIClient()
    client.force_authenticate(user=sender)
    response = client.post(
        f"/api/v1/posts/{post.id}/gifts/",
        data={"gift_type_id": gift_type.id, "quantity": 1},
        format="json",
    )
    assert response.status_code == 400
    assert response.data.get("code") == "invalid_request"
