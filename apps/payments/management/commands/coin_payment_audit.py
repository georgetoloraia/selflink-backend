from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.coin.models import CoinEvent, CoinEventType
from apps.payments.models import PaymentEvent, PaymentEventProvider


class Command(BaseCommand):
    help = "Audit payment events against SLC mint events."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--provider", default="stripe", help="Payment provider name (default: stripe).")
        parser.add_argument("--limit", type=int, default=50, help="Max rows to print per section.")
        parser.add_argument("--show", action="store_true", default=False, help="Print row details.")

    def handle(self, *args, **options):
        provider = str(options.get("provider") or "").strip().lower()
        if provider not in PaymentEventProvider.values:
            raise CommandError(f"Unsupported provider: {provider}")

        limit = max(1, min(int(options.get("limit") or 50), 500))
        show = bool(options.get("show"))

        events = PaymentEvent.objects.filter(provider=provider).order_by("created_at", "id")
        unminted = events.filter(minted_coin_event__isnull=True)

        self.stdout.write(self.style.NOTICE(f"provider={provider} total_events={events.count()}"))
        self.stdout.write(self.style.WARNING(f"unminted_events={unminted.count()}"))
        if show:
            for event in unminted[:limit]:
                self.stdout.write(
                    f"- id={event.id} provider_event_id={event.provider_event_id} user_id={event.user_id} "
                    f"amount_cents={event.amount_cents} status={event.status}"
                )

        missing_payment = (
            CoinEvent.objects.filter(event_type=CoinEventType.MINT, idempotency_key__startswith=f"{provider}:")
            .filter(payment_events__isnull=True)
            .order_by("created_at", "id")
        )
        self.stdout.write(self.style.ERROR(f"mint_events_without_payment_event={missing_payment.count()}"))
        if show:
            for event in missing_payment[:limit]:
                self.stdout.write(
                    f"- coin_event_id={event.id} idempotency_key={event.idempotency_key} created_at={event.created_at.isoformat()}"
                )
