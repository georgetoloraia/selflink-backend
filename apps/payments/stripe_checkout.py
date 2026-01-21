from __future__ import annotations

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.clients import get_stripe_client
from apps.payments.feature_flag import provider_enabled
from apps.payments.serializers import StripeCheckoutCreateSerializer


class StripeCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not provider_enabled("stripe"):
            return Response({"detail": "Stripe disabled"}, status=status.HTTP_403_FORBIDDEN)
        serializer = StripeCheckoutCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        checkout = serializer.save()

        client = get_stripe_client()
        session = client.create_checkout_payment_session(
            amount_cents=checkout.amount_cents,
            currency=checkout.currency,
            success_url=settings.STRIPE_CHECKOUT_SUCCESS_URL,
            cancel_url=settings.STRIPE_CHECKOUT_CANCEL_URL,
            reference=checkout.reference,
            metadata={"reference": checkout.reference},
        )

        return Response(
            {
                "checkout_id": checkout.id,
                "reference": checkout.reference,
                "amount_cents": checkout.amount_cents,
                "currency": checkout.currency,
                "status": checkout.status,
                "payment_url": session.url,
            },
            status=status.HTTP_201_CREATED,
        )
