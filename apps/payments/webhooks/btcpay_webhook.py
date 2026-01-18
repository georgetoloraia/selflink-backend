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
from apps.payments.feature_flag import payments_enabled
from apps.payments.models import PaymentCheckout, PaymentEvent
from apps.payments.providers.btcpay import (
    get_btcpay_client,
    normalize_invoice,
    parse_webhook_event,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return request.META.get("HTTP_X_REQUEST_ID", "")


@method_decorator(csrf_exempt, name="dispatch")
class BtcPayWebhookView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        if not payments_enabled():
            return Response(status=status.HTTP_403_FORBIDDEN)

        req_id = _request_id(request)
        try:
            verify_webhook_signature(request)
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning("btcpay_mint.rejected request_id=%s reason=invalid_signature detail=%s", req_id, detail)
            return Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            event = parse_webhook_event(request.body)
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning("btcpay_mint.rejected request_id=%s reason=invalid_payload detail=%s", req_id, detail)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        client = get_btcpay_client()
        try:
            invoice_payload = client.get_invoice(invoice_id=event.invoice_id)
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning("btcpay_mint.rejected request_id=%s reason=invoice_fetch_failed detail=%s", req_id, detail)
            return Response({"detail": detail}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            invoice = normalize_invoice(invoice_payload)
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning("btcpay_mint.rejected request_id=%s reason=invalid_invoice detail=%s", req_id, detail)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        checkout = PaymentCheckout.objects.select_related("user").filter(
            provider=PaymentEvent.Provider.BTCPAY,
            provider_reference=invoice.invoice_id,
        ).first()
        if not checkout and invoice.reference:
            checkout = PaymentCheckout.objects.select_related("user").filter(
                provider=PaymentEvent.Provider.BTCPAY,
                reference=invoice.reference,
            ).first()

        if not checkout:
            logger.warning(
                "btcpay_mint.rejected request_id=%s reason=unknown_reference invoice_id=%s",
                req_id,
                invoice.invoice_id,
            )
            return Response({"detail": "Unknown payment reference."}, status=status.HTTP_400_BAD_REQUEST)

        if invoice.reference and invoice.reference != checkout.reference:
            logger.warning(
                "btcpay_mint.rejected request_id=%s reason=reference_mismatch invoice_id=%s",
                req_id,
                invoice.invoice_id,
            )
            return Response({"detail": "Payment reference mismatch."}, status=status.HTTP_400_BAD_REQUEST)

        if checkout.amount_cents != invoice.amount_cents or checkout.currency != invoice.currency:
            logger.warning(
                "btcpay_mint.rejected request_id=%s reason=amount_mismatch reference=%s expected=%s %s got=%s %s",
                req_id,
                checkout.reference,
                checkout.amount_cents,
                checkout.currency,
                invoice.amount_cents,
                invoice.currency,
            )
            return Response({"detail": "Payment amount mismatch."}, status=status.HTTP_400_BAD_REQUEST)

        if checkout.provider_reference != invoice.invoice_id:
            checkout.provider_reference = invoice.invoice_id
            checkout.save(update_fields=["provider_reference", "updated_at"])

        paid_statuses = {status.lower() for status in (getattr(settings, "BTCPAY_PAID_STATUSES", []) or [])}
        failed_statuses = {status.lower() for status in (getattr(settings, "BTCPAY_FAILED_STATUSES", []) or [])}

        raw_body_hash = hashlib.sha256(request.body).hexdigest()
        verified_at = timezone.now()

        status_value = PaymentEvent.Status.RECEIVED
        if invoice.status in failed_statuses:
            status_value = PaymentEvent.Status.FAILED

        try:
            payment_event, created = PaymentEvent.objects.get_or_create(
                provider=PaymentEvent.Provider.BTCPAY,
                provider_event_id=invoice.invoice_id,
                defaults={
                    "event_type": event.event_type,
                    "user": checkout.user,
                    "amount_cents": invoice.amount_cents,
                    "currency": invoice.currency,
                    "status": status_value,
                    "raw_body_hash": raw_body_hash,
                    "verified_at": verified_at,
                },
            )
        except IntegrityError:
            payment_event = PaymentEvent.objects.filter(
                provider=PaymentEvent.Provider.BTCPAY,
                provider_event_id=invoice.invoice_id,
            ).first()
            created = False

        if not payment_event:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not created:
            if (
                payment_event.user_id != checkout.user_id
                or payment_event.amount_cents != invoice.amount_cents
                or payment_event.currency != invoice.currency
            ):
                logger.warning(
                    "btcpay_mint.rejected request_id=%s reason=payment_event_mismatch invoice_id=%s",
                    req_id,
                    invoice.invoice_id,
                )
                return Response({"detail": "Payment event mismatch."}, status=status.HTTP_400_BAD_REQUEST)
            if payment_event.verified_at is None:
                payment_event.verified_at = verified_at
                payment_event.save(update_fields=["verified_at", "updated_at"])
            if invoice.status in failed_statuses and payment_event.status != PaymentEvent.Status.FAILED:
                payment_event.status = PaymentEvent.Status.FAILED
                payment_event.save(update_fields=["status", "updated_at"])
            if payment_event.minted_coin_event_id:
                checkout.status = PaymentCheckout.Status.PAID
                checkout.save(update_fields=["status", "updated_at"])
                logger.info(
                    "btcpay_mint.duplicate request_id=%s invoice_id=%s user_id=%s amount_cents=%s",
                    req_id,
                    invoice.invoice_id,
                    checkout.user_id,
                    invoice.amount_cents,
                )
                return Response({"received": True})

        if invoice.status in failed_statuses:
            checkout.status = PaymentCheckout.Status.FAILED
            checkout.save(update_fields=["status", "updated_at"])
            logger.info(
                "btcpay_mint.skipped request_id=%s reason=failed_status invoice_id=%s status=%s",
                req_id,
                invoice.invoice_id,
                invoice.status,
            )
            return Response({"received": True})

        if invoice.status not in paid_statuses:
            logger.info(
                "btcpay_mint.skipped request_id=%s reason=non_final_status invoice_id=%s status=%s",
                req_id,
                invoice.invoice_id,
                invoice.status,
            )
            return Response({"received": True})

        try:
            minted_event = mint_from_payment_event(
                payment_event=payment_event,
                metadata={"source": "btcpay_webhook", "reference": checkout.reference},
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            logger.warning(
                "btcpay_mint.rejected request_id=%s invoice_id=%s reason=%s",
                req_id,
                invoice.invoice_id,
                detail,
            )
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        payment_event.minted_coin_event = minted_event
        payment_event.status = PaymentEvent.Status.MINTED
        payment_event.save(update_fields=["minted_coin_event", "status", "updated_at"])
        checkout.status = PaymentCheckout.Status.PAID
        checkout.save(update_fields=["status", "updated_at"])

        logger.info(
            "btcpay_mint.accepted request_id=%s invoice_id=%s user_id=%s amount_cents=%s coin_event_id=%s",
            req_id,
            invoice.invoice_id,
            checkout.user_id,
            invoice.amount_cents,
            minted_event.id,
        )
        return Response({"received": True})
