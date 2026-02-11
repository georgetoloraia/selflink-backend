from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.messaging.models import Message, Thread, ThreadMember
from apps.payments.models import GiftType, Plan, Subscription, Wallet, SubscriptionStatus
from apps.social.models import Follow, Post, PostVisibility
from apps.users.models import User, UserSettings

DEMO_USERS = [
    {
        "email": "demo-mentor@example.com",
        "handle": "mentor",
        "name": "Demo Mentor",
        "bio": "AI mentor persona used for demos.",
    },
    {
        "email": "demo-seeker@example.com",
        "handle": "seeker",
        "name": "Demo Seeker",
        "bio": "Looking for resonance and conscious connection.",
    },
    {
        "email": "demo-builder@example.com",
        "handle": "builder",
        "name": "Demo Builder",
        "bio": "Community builder and guide.",
    },
]

DEFAULT_PASSWORD = "changeme123"


class Command(BaseCommand):
    help = "Seed demo data for SelfLink backend"

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset demo users before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("reset"):
            self.stdout.write("Removing existing demo data…")
            emails = [user["email"] for user in DEMO_USERS]
            User.objects.filter(email__in=emails).delete()

        self._ensure_plans()
        self._ensure_gift_types()

        users = [self._ensure_user(payload) for payload in DEMO_USERS]
        self._ensure_follow_graph(users)
        self._ensure_posts(users)
        self._ensure_messaging(users)
        self._ensure_subscriptions(users)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    def _ensure_user(self, payload: dict) -> User:
        user, created = User.objects.get_or_create(
            email=payload["email"],
            defaults={
                "handle": payload["handle"],
                "name": payload["name"],
                "bio": payload.get("bio", ""),
                "locale": "en-US",
                "birth_date": date(1990, 1, 1) + timedelta(days=random.randint(0, 365)),
            },
        )
        if created or not user.check_password(DEFAULT_PASSWORD):
            user.set_password(DEFAULT_PASSWORD)
            user.save(update_fields=["password"])
        UserSettings.objects.get_or_create(user=user)
        return user

    def _ensure_plans(self) -> None:
        Plan.objects.update_or_create(
            name="Free",
            defaults={
                "price_cents": 0,
                "interval": "month",
                "features": {
                    "mentor": "Basic mentor guidance",
                    "matrix": "Core astro matrix",
                },
                "is_active": True,
            },
        )
        Plan.objects.update_or_create(
            name="Premium",
            defaults={
                "price_cents": 900,
                "interval": "month",
                "features": {
                    "mentor": "Mentor+ insights",
                    "matrix": "Deep resonance analytics",
                    "soulmatch": "Compatibility filtering",
                },
                "is_active": True,
            },
        )

    def _ensure_gift_types(self) -> None:
        GiftType.objects.update_or_create(
            name="Starlight",
            defaults={
                "price_cents": 100,
                "metadata": {"description": "A gentle burst of light"},
            },
        )
        GiftType.objects.update_or_create(
            name="Aurora",
            defaults={
                "price_cents": 250,
                "metadata": {"description": "Immersive aurora animation"},
            },
        )

    def _ensure_follow_graph(self, users: list[User]) -> None:
        if len(users) < 2:
            return
        for follower in users:
            for followee in users:
                if follower == followee:
                    continue
                Follow.objects.get_or_create(follower=follower, followee=followee)

    def _ensure_posts(self, users: list[User]) -> None:
        if not users:
            return
        sample_posts = [
            "Today I practiced a 5-minute grounding breath and felt calmer.",
            "Shared a gratitude note with a friend – it opened a long conversation.",
            "Explored my life path number again; noticing repeating cycles.",
        ]
        for idx, text in enumerate(sample_posts):
            author = users[idx % len(users)]
            Post.objects.get_or_create(
                author=author,
                text=text,
                defaults={
                    "visibility": PostVisibility.PUBLIC,
                    "language": "en",
                },
            )

    def _ensure_messaging(self, users: list[User]) -> None:
        if len(users) < 2:
            return
        thread, _ = Thread.objects.get_or_create(
            title="Demo Chat",
            defaults={
                "is_group": True,
                "created_by": users[0],
            },
        )
        for user in users:
            ThreadMember.objects.get_or_create(thread=thread, user=user)
        Message.objects.get_or_create(
            thread=thread,
            sender=users[0],
            body="Welcome to the SelfLink demo space!",
        )

    def _ensure_subscriptions(self, users: list[User]) -> None:
        premium = Plan.objects.filter(name="Premium").first()
        if not premium:
            return
        for user in users[1:]:  # upgrade a couple of demo accounts
            Subscription.objects.update_or_create(
                user=user,
                plan=premium,
                defaults={"status": SubscriptionStatus.ACTIVE},
            )
            Wallet.objects.get_or_create(user=user)
