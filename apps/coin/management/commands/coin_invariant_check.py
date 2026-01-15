from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.db.models import Case, F, Sum, When

from apps.coin.models import CoinAccount, CoinEvent, CoinLedgerEntry, SYSTEM_ACCOUNT_KEYS
from apps.payments.models import PaymentEvent


class Command(BaseCommand):
    help = "Validate SLC ledger invariants (read-only)."

    def handle(self, *args, **options) -> None:
        failures: list[str] = []

        mint_events = CoinEvent.objects.filter(event_type=CoinEvent.EventType.MINT)
        missing_payment = mint_events.filter(payment_events__isnull=True).distinct()
        missing_payment_count = missing_payment.count()
        if missing_payment_count:
            failures.append(f"mint_events_without_payment_event={missing_payment_count}")

        non_minted_payment = (
            mint_events.filter(payment_events__isnull=False)
            .exclude(payment_events__status=PaymentEvent.Status.MINTED)
            .distinct()
        )
        non_minted_payment_count = non_minted_payment.count()
        if non_minted_payment_count:
            failures.append(f"mint_events_with_non_minted_payment_event={non_minted_payment_count}")

        payment_wrong_type = PaymentEvent.objects.filter(minted_coin_event__isnull=False).exclude(
            minted_coin_event__event_type=CoinEvent.EventType.MINT
        )
        payment_wrong_type_count = payment_wrong_type.count()
        if payment_wrong_type_count:
            failures.append(f"payment_events_linked_to_non_mint_event={payment_wrong_type_count}")

        unbalanced = (
            CoinLedgerEntry.objects.values("event_id", "currency")
            .annotate(
                total=Sum(
                    Case(
                        When(direction=CoinLedgerEntry.Direction.CREDIT, then=F("amount_cents")),
                        When(direction=CoinLedgerEntry.Direction.DEBIT, then=-F("amount_cents")),
                        default=0,
                        output_field=models.BigIntegerField(),
                    )
                )
            )
            .filter(~models.Q(total=0))
        )
        unbalanced_count = unbalanced.count()
        if unbalanced_count:
            failures.append(f"unbalanced_event_groups={unbalanced_count}")

        unknown_accounts = CoinLedgerEntry.objects.exclude(
            account_key__in=CoinAccount.objects.values("account_key")
        )
        unknown_accounts_count = unknown_accounts.count()
        if unknown_accounts_count:
            failures.append(f"unknown_account_entries={unknown_accounts_count}")

        suspended_accounts = CoinAccount.objects.filter(status=CoinAccount.Status.SUSPENDED).exclude(
            account_key__in=SYSTEM_ACCOUNT_KEYS
        )
        suspended_entries = CoinLedgerEntry.objects.filter(
            account_key__in=suspended_accounts.values("account_key")
        )
        suspended_entries_count = suspended_entries.count()
        if suspended_entries_count:
            failures.append(f"suspended_account_entries={suspended_entries_count}")

        self.stdout.write("coin_invariant_check:")
        self.stdout.write(f"- mint_events={mint_events.count()}")
        self.stdout.write(f"- mint_events_without_payment_event={missing_payment_count}")
        self.stdout.write(f"- mint_events_with_non_minted_payment_event={non_minted_payment_count}")
        self.stdout.write(f"- payment_events_linked_to_non_mint_event={payment_wrong_type_count}")
        self.stdout.write(f"- unbalanced_event_groups={unbalanced_count}")
        self.stdout.write(f"- unknown_account_entries={unknown_accounts_count}")
        self.stdout.write(f"- suspended_account_entries={suspended_entries_count}")

        if failures:
            raise CommandError("coin_invariant_check failed: " + "; ".join(failures))
