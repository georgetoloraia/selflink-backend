from __future__ import annotations

import os
from typing import Any, Dict, Optional

import stripe


class StripeClient:
    def __init__(self, api_key: str, webhook_secret: str | None = None) -> None:
        stripe.api_key = api_key
        self.webhook_secret = webhook_secret

    def create_customer(self, email: str, metadata: Optional[Dict[str, Any]] = None) -> stripe.Customer:
        return stripe.Customer.create(email=email, metadata=metadata or {})

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> stripe.checkout.Session:
        return stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )

    def retrieve_subscription(self, subscription_id: str) -> stripe.Subscription:
        return stripe.Subscription.retrieve(subscription_id)

    def construct_event(self, payload: bytes, signature: str) -> stripe.Event:
        if not self.webhook_secret:
            raise ValueError("Webhook secret not configured")
        return stripe.Webhook.construct_event(payload, signature, self.webhook_secret)


def get_stripe_client(overrides: Optional[Dict[str, Any]] = None) -> StripeClient:
    api_key = (overrides or {}).get("api_key") or os.getenv("STRIPE_API_KEY")
    if not api_key:
        raise RuntimeError("STRIPE_API_KEY is not set")
    webhook_secret = (overrides or {}).get("webhook_secret") or os.getenv("STRIPE_WEBHOOK_SECRET")
    return StripeClient(api_key=api_key, webhook_secret=webhook_secret)
