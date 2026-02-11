from __future__ import annotations

import hashlib
import logging

from django.conf import settings
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
from apps.payments.feature_flag import provider_enabled
from apps.payments.models import PaymentCheckout, PaymentEvent, PaymentEventProvider, PaymentEventStatus, PaymentCheckoutStatus
from apps.payments.providers.ipay import parse_event, verify_webhook_signature

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return request.META.get("HTTP_X_REQUEST_ID", "")


@method_decorator(csrf_exempt, name="dispatch")
class IpayWebhookView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        if not provider_enabled("ipay"):
            return Response(status=status.HTTP_403_FORBIDDEN)

        req_id = _request_id(request)
        try:
            verify_webhook_signature(request)
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning("ipay_mint.rejected request_id=%s reason=invalid_signature detail=%s", req_id, detail)
            return Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            event = parse_event(request.body)
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning("ipay_mint.rejected request_id=%s reason=invalid_payload detail=%s", req_id, detail)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        checkout = PaymentCheckout.objects.select_related("user").filter(
            provider=PaymentEventProvider.IPAY,
            reference=event.reference,
        ).first()
        if not checkout:
            logger.warning("ipay_mint.rejected request_id=%s reason=unknown_reference reference=%s", req_id, event.reference)
            return Response({"detail": "Unknown payment reference."}, status=status.HTTP_400_BAD_REQUEST)

        if checkout.amount_cents != event.amount_cents or checkout.currency != event.currency:
            logger.warning(
                "ipay_mint.rejected request_id=%s reason=amount_mismatch reference=%s expected=%s %s got=%s %s",
                req_id,
                checkout.reference,
                checkout.amount_cents,
                checkout.currency,
                event.amount_cents,
                event.currency,
            )
            return Response({"detail": "Payment amount mismatch."}, status=status.HTTP_400_BAD_REQUEST)

        paid_statuses = {status.lower() for status in (getattr(settings, "IPAY_PAID_STATUSES", []) or [])}
        failed_statuses = {status.lower() for status in (getattr(settings, "IPAY_FAILED_STATUSES", []) or [])}

        raw_body_hash = hashlib.sha256(request.body).hexdigest()
        verified_at = timezone.now()

        status_value = PaymentEventStatus.RECEIVED
        if event.status in failed_statuses:
            status_value = PaymentEventStatus.FAILED

        try:
            payment_event, created = PaymentEvent.objects.get_or_create(
                provider=PaymentEventProvider.IPAY,
                provider_event_id=event.provider_event_id,
                defaults={
                    "event_type": event.event_type,
                    "user": checkout.user,
                    "amount_cents": event.amount_cents,
                    "currency": event.currency,
                    "status": status_value,
                    "raw_body_hash": raw_body_hash,
                    "verified_at": verified_at,
                },
            )
        except IntegrityError:
            payment_event = PaymentEvent.objects.filter(
                provider=PaymentEventProvider.IPAY,
                provider_event_id=event.provider_event_id,
            ).first()
            created = False

        if not payment_event:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not created:
            if (
                payment_event.user_id != checkout.user_id
                or payment_event.amount_cents != event.amount_cents
                or payment_event.currency != event.currency
            ):
                logger.warning(
                    "ipay_mint.rejected request_id=%s reason=payment_event_mismatch event_id=%s",
                    req_id,
                    event.provider_event_id,
                )
                return Response({"detail": "Payment event mismatch."}, status=status.HTTP_400_BAD_REQUEST)
            if payment_event.verified_at is None:
                payment_event.verified_at = verified_at
                payment_event.save(update_fields=["verified_at", "updated_at"])
            if event.status in failed_statuses and payment_event.status != PaymentEventStatus.FAILED:
                payment_event.status = PaymentEventStatus.FAILED
                payment_event.save(update_fields=["status", "updated_at"])
            if payment_event.minted_coin_event_id:
                checkout.status = PaymentCheckoutStatus.PAID
                checkout.save(update_fields=["status", "updated_at"])
                logger.info(
                    "ipay_mint.duplicate request_id=%s event_id=%s user_id=%s amount_cents=%s",
                    req_id,
                    event.provider_event_id,
                    checkout.user_id,
                    event.amount_cents,
                )
                return Response({"received": True})

        if event.status in failed_statuses:
            checkout.status = PaymentCheckoutStatus.FAILED
            checkout.save(update_fields=["status", "updated_at"])
            logger.info(
                "ipay_mint.skipped request_id=%s reason=failed_status event_id=%s status=%s",
                req_id,
                event.provider_event_id,
                event.status,
            )
            return Response({"received": True})

        if event.status not in paid_statuses:
            logger.info(
                "ipay_mint.skipped request_id=%s reason=non_final_status event_id=%s status=%s",
                req_id,
                event.provider_event_id,
                event.status,
            )
            return Response({"received": True})

        try:
            minted_event = mint_from_payment_event(
                payment_event=payment_event,
                metadata={"source": "ipay_webhook", "reference": checkout.reference},
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning(
                "ipay_mint.rejected request_id=%s event_id=%s reason=%s",
                req_id,
                event.provider_event_id,
                detail,
            )
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        payment_event.minted_coin_event = minted_event
        payment_event.status = PaymentEventStatus.MINTED
        payment_event.save(update_fields=["minted_coin_event", "status", "updated_at"])
        checkout.status = PaymentCheckoutStatus.PAID
        checkout.save(update_fields=["status", "updated_at"])

        logger.info(
            "ipay_mint.accepted request_id=%s event_id=%s user_id=%s amount_cents=%s coin_event_id=%s",
            req_id,
            event.provider_event_id,
            checkout.user_id,
            event.amount_cents,
            minted_event.id,
        )
        return Response({"received": True})
