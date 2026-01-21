from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.feature_flag import provider_enabled
from apps.payments.serializers import IpayCheckoutCreateSerializer


class IpayCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not provider_enabled("ipay"):
            return Response({"detail": "iPay disabled"}, status=status.HTTP_403_FORBIDDEN)
        serializer = IpayCheckoutCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        checkout = serializer.save()
        return Response(
            {
                "checkout_id": checkout.id,
                "reference": checkout.reference,
                "amount_cents": checkout.amount_cents,
                "currency": checkout.currency,
                "status": checkout.status,
            },
            status=status.HTTP_201_CREATED,
        )
