from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.utils import timezone

from apps.payments.clients import get_stripe_client
from apps.payments.models import Plan, Subscription, Wallet, SubscriptionStatus
from apps.users.models import User


@dataclass
class CheckoutSessionResult:
    subscription: Subscription
    session_id: Optional[str]
    checkout_url: Optional[str]


def ensure_wallet(user: User) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def ensure_external_customer(wallet: Wallet, user: User) -> str:
    if wallet.external_customer_id:
        return wallet.external_customer_id
    client = get_stripe_client()
    customer = client.create_customer(email=user.email, metadata={"user_id": str(user.id)})
    wallet.external_customer_id = customer.id
    wallet.save(update_fields=["external_customer_id", "updated_at"])
    return customer.id


def create_checkout_session(user: User, plan: Plan, success_url: str, cancel_url: str) -> CheckoutSessionResult:
    wallet = ensure_wallet(user)
    customer_id = ensure_external_customer(wallet, user)
    subscription, _ = Subscription.objects.get_or_create(
        user=user,
        defaults={
            "plan": plan,
            "status": SubscriptionStatus.INCOMPLETE,
        },
    )
    if subscription.plan_id != plan.id:
        subscription.plan = plan
    subscription.status = SubscriptionStatus.INCOMPLETE
    subscription.save(update_fields=["plan", "status", "updated_at"])

    if not plan.external_price_id:
        return CheckoutSessionResult(subscription=subscription, session_id=None, checkout_url=None)

    client = get_stripe_client()
    session = client.create_checkout_session(
        customer_id=customer_id,
        price_id=plan.external_price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user.id),
            "plan_id": str(plan.id),
            "subscription_id": str(subscription.id),
        },
    )
    return CheckoutSessionResult(subscription=subscription, session_id=session.id, checkout_url=session.url)


def map_stripe_status(status: str) -> str:
    status = status or ""
    mapping = {
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.ACTIVE,
        "canceled": SubscriptionStatus.CANCELED,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "incomplete_expired": SubscriptionStatus.CANCELED,
        "past_due": SubscriptionStatus.PAST_DUE,
        "unpaid": SubscriptionStatus.PAST_DUE,
    }
    return mapping.get(status, SubscriptionStatus.INCOMPLETE)


def update_subscription_from_stripe(subscription_id: str | None, stripe_subscription: dict) -> None:
    sub: Optional[Subscription] = None
    if subscription_id:
        sub = Subscription.objects.filter(id=subscription_id).first()
    if sub is None:
        sub = Subscription.objects.filter(external_subscription_id=stripe_subscription.get("id")).first()
    if sub is None:
        return

    status = map_stripe_status(stripe_subscription.get("status", ""))
    current_period_start = stripe_subscription.get("current_period_start")
    current_period_end = stripe_subscription.get("current_period_end")

    sub.status = status
    sub.external_subscription_id = stripe_subscription.get("id", "")
    sub.external_customer_id = stripe_subscription.get("customer", "")
    if current_period_start:
        sub.current_period_start = timezone.make_aware(datetime.utcfromtimestamp(current_period_start))
    if current_period_end:
        sub.current_period_end = timezone.make_aware(datetime.utcfromtimestamp(current_period_end))
    sub.save(update_fields=[
        "status",
        "external_subscription_id",
        "external_customer_id",
        "current_period_start",
        "current_period_end",
        "updated_at",
    ])

    wallet = ensure_wallet(sub.user)
    if not wallet.external_customer_id and sub.external_customer_id:
        wallet.external_customer_id = sub.external_customer_id
        wallet.save(update_fields=["external_customer_id", "updated_at"])
