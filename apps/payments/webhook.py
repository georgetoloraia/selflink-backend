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
from apps.payments.models import PaymentCheckout, PaymentEvent
from apps.payments.services import update_subscription_from_stripe
from .feature_flag import payments_enabled

logger = logging.getLogger(__name__)


def _get_checkout_reference(data: dict) -> str:
    reference = data.get("client_reference_id")
    if reference:
        return str(reference)
    metadata = data.get("metadata", {}) or {}
    reference = metadata.get("reference") or metadata.get("payment_reference")
    if reference:
        return str(reference)
    raise ValidationError("Missing payment reference.")


def _get_stripe_amount_cents(data: dict, client) -> int:
    amount_raw = data.get("amount_total")
    if amount_raw in (None, ""):
        amount_raw = data.get("amount_received")
    if amount_raw in (None, "") and data.get("payment_intent"):
        intent = client.retrieve_payment_intent(data.get("payment_intent"))
        amount_raw = getattr(intent, "amount_received", None)
    if amount_raw in (None, ""):
        raise ValidationError("Stripe amount is required for coin minting.")
    try:
        amount_cents = int(amount_raw)
    except (TypeError, ValueError):
        raise ValidationError("Stripe amount must be an integer.")
    if amount_cents <= 0:
        raise ValidationError("Stripe amount must be positive.")
    return amount_cents


def _get_stripe_currency(data: dict, client) -> str:
    currency = data.get("currency")
    if not currency and data.get("payment_intent"):
        intent = client.retrieve_payment_intent(data.get("payment_intent"))
        currency = getattr(intent, "currency", None)
    return str(currency or "USD").upper()


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
            mode = data.get("mode")
            if mode == "subscription":
                subscription_id = data.get("subscription")
                stripe_subscription = client.retrieve_subscription(subscription_id) if subscription_id else None
                if stripe_subscription:
                    update_subscription_from_stripe(metadata.get("subscription_id"), stripe_subscription)
                return Response({"received": True})

            try:
                reference = _get_checkout_reference(data)
            except ValidationError as exc:
                detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                logger.warning(
                    "coin_mint.rejected provider=stripe event_id=%s reason=%s",
                    event.get("id"),
                    detail,
                )
                return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

            checkout = PaymentCheckout.objects.select_related("user").filter(
                provider=PaymentEvent.Provider.STRIPE,
                reference=reference,
            ).first()
            if not checkout:
                logger.warning(
                    "coin_mint.rejected provider=stripe event_id=%s reason=unknown_reference reference=%s",
                    event.get("id"),
                    reference,
                )
                return Response({"detail": "Unknown payment reference."}, status=status.HTTP_400_BAD_REQUEST)

            provider_event_id = event.get("id")
            if not provider_event_id:
                logger.warning("coin_mint.rejected provider=stripe reason=missing_event_id")
                return Response(status=status.HTTP_400_BAD_REQUEST)

            payment_status = data.get("payment_status")
            try:
                amount_cents = _get_stripe_amount_cents(data, client)
            except ValidationError as exc:
                detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                logger.warning(
                    "coin_mint.rejected provider=stripe event_id=%s reason=%s",
                    provider_event_id,
                    detail,
                )
                return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
            currency = _get_stripe_currency(data, client)

            if checkout.amount_cents != amount_cents or checkout.currency != currency:
                logger.warning(
                    "coin_mint.rejected provider=stripe event_id=%s reason=amount_mismatch reference=%s",
                    provider_event_id,
                    reference,
                )
                return Response({"detail": "Payment amount mismatch."}, status=status.HTTP_400_BAD_REQUEST)

            raw_body_hash = hashlib.sha256(request.body).hexdigest()
            verified_at = timezone.now()
            status_value = PaymentEvent.Status.RECEIVED
            if payment_status == "unpaid":
                status_value = PaymentEvent.Status.FAILED

            try:
                payment_event, created = PaymentEvent.objects.get_or_create(
                    provider=PaymentEvent.Provider.STRIPE,
                    provider_event_id=provider_event_id,
                    defaults={
                        "event_type": event_type or "",
                        "user": checkout.user,
                        "amount_cents": amount_cents,
                        "currency": currency,
                        "status": status_value,
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
                if (
                    payment_event.user_id != checkout.user_id
                    or payment_event.amount_cents != amount_cents
                    or payment_event.currency != currency
                ):
                    logger.warning(
                        "coin_mint.rejected provider=stripe event_id=%s reason=payment_event_mismatch",
                        provider_event_id,
                    )
                    return Response({"detail": "Payment event mismatch."}, status=status.HTTP_400_BAD_REQUEST)
                if payment_event.verified_at is None:
                    payment_event.verified_at = verified_at
                    payment_event.save(update_fields=["verified_at", "updated_at"])
                if payment_event.status != status_value and status_value == PaymentEvent.Status.FAILED:
                    payment_event.status = status_value
                    payment_event.save(update_fields=["status", "updated_at"])
                if payment_event.minted_coin_event_id:
                    checkout.status = PaymentCheckout.Status.PAID
                    checkout.save(update_fields=["status", "updated_at"])
                    logger.info(
                        "coin_mint.duplicate provider=stripe event_id=%s user_id=%s amount_cents=%s",
                        provider_event_id,
                        checkout.user_id,
                        amount_cents,
                    )
                    return Response({"received": True})

            if payment_status != "paid":
                logger.info(
                    "coin_mint.skipped provider=stripe event_id=%s status=%s",
                    provider_event_id,
                    payment_status,
                )
                if status_value == PaymentEvent.Status.FAILED:
                    checkout.status = PaymentCheckout.Status.FAILED
                    checkout.save(update_fields=["status", "updated_at"])
                return Response({"received": True})

            try:
                minted_event = mint_from_payment_event(
                    payment_event=payment_event,
                    metadata={"source": "stripe_webhook", "reference": reference},
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
            checkout.status = PaymentCheckout.Status.PAID
            checkout.save(update_fields=["status", "updated_at"])
            logger.info(
                "coin_mint.accepted provider=stripe event_id=%s user_id=%s amount_cents=%s coin_event_id=%s",
                provider_event_id,
                checkout.user_id,
                amount_cents,
                minted_event.id,
            )
        elif event_type in {"customer.subscription.updated", "customer.subscription.created", "customer.subscription.deleted"}:
            metadata = data.get("metadata", {})
            update_subscription_from_stripe(metadata.get("subscription_id"), data)

        return Response({"received": True})
