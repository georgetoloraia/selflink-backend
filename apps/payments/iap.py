from __future__ import annotations

import hashlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.coin.services.ledger import get_balance_cents, get_or_create_user_account
from apps.coin.services.payments import mint_from_payment_event
from apps.payments.feature_flag import provider_enabled
from apps.payments.models import PaymentEvent, PaymentEventProvider, PaymentEventStatus
from apps.payments.providers.iap.apple import verify_apple_receipt
from apps.payments.providers.iap.google import verify_google_purchase
from apps.payments.serializers import IapVerifySerializer


class IapVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "iap_verify"

    def post(self, request: Request) -> Response:
        if not provider_enabled("iap"):
            return Response({"detail": "IAP disabled"}, status=status.HTTP_403_FORBIDDEN)

        serializer = IapVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        platform = serializer.validated_data["platform"]
        product_id = serializer.validated_data["product_id"]
        transaction_id = serializer.validated_data["transaction_id"]

        sku_map = getattr(settings, "IAP_SKU_MAP", {}) or {}
        sku = sku_map.get(product_id)
        if not isinstance(sku, dict):
            return Response({"detail": "Unknown product_id."}, status=status.HTTP_400_BAD_REQUEST)

        amount_cents = int(sku.get("amount_cents", 0))
        currency = str(sku.get("currency", "USD")).upper()
        if amount_cents <= 0:
            return Response({"detail": "SKU amount invalid."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if platform == "ios":
                receipt = serializer.validated_data.get("receipt", "")
                result = verify_apple_receipt(
                    receipt=receipt,
                    expected_product_id=product_id,
                    expected_transaction_id=transaction_id,
                )
                provider = PaymentEventProvider.APPLE_IAP
            else:
                purchase_token = serializer.validated_data.get("purchase_token", "")
                result = verify_google_purchase(
                    purchase_token=purchase_token,
                    expected_product_id=product_id,
                    expected_order_id=transaction_id,
                )
                provider = PaymentEventProvider.GOOGLE_IAP
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        if not result.ok:
            return Response({"detail": "Verification failed."}, status=status.HTTP_400_BAD_REQUEST)
        if str(result.status).lower() != "paid":
            return Response({"detail": "Purchase not settled."}, status=status.HTTP_409_CONFLICT)

        provider_event_id = result.provider_event_id or transaction_id
        raw_body_hash = hashlib.sha256(request.body).hexdigest()
        verified_at = timezone.now()

        payment_event, created = PaymentEvent.objects.get_or_create(
            provider=provider,
            provider_event_id=provider_event_id,
            defaults={
                "event_type": "iap.verify",
                "user": request.user,
                "amount_cents": amount_cents,
                "currency": currency,
                "status": PaymentEventStatus.RECEIVED,
                "raw_body_hash": raw_body_hash,
                "verified_at": verified_at,
            },
        )

        if not created:
            if (
                payment_event.user_id != request.user.id
                or payment_event.amount_cents != amount_cents
                or payment_event.currency != currency
            ):
                return Response({"detail": "Payment event mismatch."}, status=status.HTTP_400_BAD_REQUEST)
            if payment_event.verified_at is None:
                payment_event.verified_at = verified_at
                payment_event.save(update_fields=["verified_at", "updated_at"])
            if payment_event.minted_coin_event_id:
                account = get_or_create_user_account(request.user)
                balance_cents = get_balance_cents(account.account_key)
                return Response(
                    {
                        "received": True,
                        "provider": provider,
                        "provider_event_id": provider_event_id,
                        "coin_event_id": payment_event.minted_coin_event_id,
                        "balance_cents": balance_cents,
                        "currency": currency,
                    },
                    status=status.HTTP_200_OK,
                )

        try:
            minted_event = mint_from_payment_event(
                payment_event=payment_event,
                metadata={"source": "iap_verify", "platform": platform, "product_id": product_id},
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        payment_event.minted_coin_event = minted_event
        payment_event.status = PaymentEventStatus.MINTED
        payment_event.save(update_fields=["minted_coin_event", "status", "updated_at"])

        account = get_or_create_user_account(request.user)
        balance_cents = get_balance_cents(account.account_key)
        return Response(
            {
                "received": True,
                "provider": provider,
                "provider_event_id": provider_event_id,
                "coin_event_id": minted_event.id,
                "balance_cents": balance_cents,
                "currency": currency,
            },
            status=status.HTTP_200_OK,
        )
