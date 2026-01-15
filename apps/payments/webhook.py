from __future__ import annotations

import hashlib
import logging

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.coin.services.payments import mint_from_payment_event
from apps.payments.clients import get_stripe_client
from apps.payments.models import PaymentEvent
from apps.payments.services import update_subscription_from_stripe
from apps.users.models import User
from .feature_flag import payments_enabled

logger = logging.getLogger(__name__)


def _parse_coin_metadata(metadata: dict) -> User | None:
    user_id_raw = metadata.get("user_id") or metadata.get("coin_user_id")
    if not user_id_raw:
        return None
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise ValidationError("user_id must be an integer.")
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ValidationError("User not found for coin minting.")
    return user


def _get_stripe_amount_cents(data: dict) -> int:
    amount_raw = data.get("amount_total")
    if amount_raw in (None, ""):
        amount_raw = data.get("amount_received")
    if amount_raw in (None, ""):
        raise ValidationError("Stripe amount is required for coin minting.")
    try:
        amount_cents = int(amount_raw)
    except (TypeError, ValueError):
        raise ValidationError("Stripe amount must be an integer.")
    if amount_cents <= 0:
        raise ValidationError("Stripe amount must be positive.")
    return amount_cents


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        client = get_stripe_client()
        if not payments_enabled():
            return Response(status=status.HTTP_403_FORBIDDEN)
        signature = request.META.get("HTTP_STRIPE_SIGNATURE")
        if not signature:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            event = client.construct_event(request.body, signature)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            metadata = data.get("metadata", {})
            subscription_id = data.get("subscription")
            stripe_subscription = client.retrieve_subscription(subscription_id) if subscription_id else None
            if stripe_subscription:
                update_subscription_from_stripe(metadata.get("subscription_id"), stripe_subscription)
            try:
                coin_user = _parse_coin_metadata(metadata)
            except ValidationError as exc:
                detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                logger.warning(
                    "coin_mint.rejected provider=stripe event_id=%s reason=%s",
                    event.get("id"),
                    detail,
                )
                return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
            if coin_user:
                payment_status = data.get("payment_status")
                if payment_status != "paid":
                    logger.warning(
                        "coin_mint.rejected provider=stripe event_id=%s reason=payment_not_paid",
                        event.get("id"),
                    )
                    return Response({"detail": "Payment not paid."}, status=status.HTTP_400_BAD_REQUEST)
                provider_event_id = event.get("id")
                if not provider_event_id:
                    logger.warning("coin_mint.rejected provider=stripe reason=missing_event_id")
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                user = coin_user
                try:
                    amount_cents = _get_stripe_amount_cents(data)
                except ValidationError as exc:
                    detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                    logger.warning(
                        "coin_mint.rejected provider=stripe event_id=%s reason=%s",
                        provider_event_id,
                        detail,
                    )
                    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
                raw_body_hash = hashlib.sha256(request.body).hexdigest()
                verified_at = timezone.now()
                try:
                    payment_event, created = PaymentEvent.objects.get_or_create(
                        provider=PaymentEvent.Provider.STRIPE,
                        provider_event_id=provider_event_id,
                        defaults={
                            "event_type": event_type or "",
                            "user": user,
                            "amount_cents": amount_cents,
                            "status": PaymentEvent.Status.RECEIVED,
                            "raw_body_hash": raw_body_hash,
                            "verified_at": verified_at,
                        },
                    )
                except IntegrityError:
                    payment_event = PaymentEvent.objects.filter(
                        provider=PaymentEvent.Provider.STRIPE,
                        provider_event_id=provider_event_id,
                    ).first()
                    created = False
                if not payment_event:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                if not created:
                    if payment_event.user_id != user.id or payment_event.amount_cents != amount_cents:
                        logger.warning(
                            "coin_mint.rejected provider=stripe event_id=%s reason=metadata_mismatch",
                            provider_event_id,
                        )
                        return Response({"detail": "Payment event metadata mismatch."}, status=status.HTTP_400_BAD_REQUEST)
                    if payment_event.verified_at is None:
                        payment_event.verified_at = verified_at
                        payment_event.save(update_fields=["verified_at", "updated_at"])
                    if payment_event.minted_coin_event_id:
                        logger.info(
                            "coin_mint.duplicate provider=stripe event_id=%s user_id=%s amount_cents=%s",
                            provider_event_id,
                            user.id,
                            amount_cents,
                        )
                        return Response({"received": True})
                try:
                    minted_event = mint_from_payment_event(
                        payment_event=payment_event,
                        metadata={"source": "stripe_webhook", "event_type": event_type or ""},
                    )
                except ValidationError as exc:
                    detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                    logger.warning(
                        "coin_mint.rejected provider=stripe event_id=%s reason=%s",
                        provider_event_id,
                        detail,
                    )
                    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
                payment_event.minted_coin_event = minted_event
                payment_event.status = PaymentEvent.Status.MINTED
                payment_event.save(update_fields=["minted_coin_event", "status", "updated_at"])
                logger.info(
                    "coin_mint.accepted provider=stripe event_id=%s user_id=%s amount_cents=%s coin_event_id=%s",
                    provider_event_id,
                    user.id,
                    amount_cents,
                    minted_event.id,
                )
        elif event_type in {"customer.subscription.updated", "customer.subscription.created", "customer.subscription.deleted"}:
            metadata = data.get("metadata", {})
            update_subscription_from_stripe(metadata.get("subscription_id"), data)

        return Response({"received": True})
