from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.clients import get_stripe_client
from apps.payments.services import update_subscription_from_stripe
from .feature_flag import payments_enabled


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
        elif event_type in {"customer.subscription.updated", "customer.subscription.created", "customer.subscription.deleted"}:
            metadata = data.get("metadata", {})
            update_subscription_from_stripe(metadata.get("subscription_id"), data)

        return Response({"received": True})
