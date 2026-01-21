from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.feature_flag import provider_enabled
from apps.payments.providers.btcpay import get_btcpay_client
from apps.payments.serializers import BtcPayCheckoutCreateSerializer


class BtcPayCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not provider_enabled("btcpay"):
            return Response({"detail": "BTCPay disabled"}, status=status.HTTP_403_FORBIDDEN)
        serializer = BtcPayCheckoutCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        checkout = serializer.save()

        client = get_btcpay_client()
        invoice = client.create_invoice(
            amount_cents=checkout.amount_cents,
            currency=checkout.currency,
            reference=checkout.reference,
        )
        checkout.provider_reference = invoice.invoice_id
        checkout.save(update_fields=["provider_reference", "updated_at"])

        return Response(
            {
                "checkout_id": checkout.id,
                "reference": checkout.reference,
                "amount_cents": checkout.amount_cents,
                "currency": checkout.currency,
                "status": checkout.status,
                "payment_url": invoice.checkout_url,
            },
            status=status.HTTP_201_CREATED,
        )
