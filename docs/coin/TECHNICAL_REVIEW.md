# SLC Technical Review

This document summarizes how the SLC ledger works and where invariants are enforced.

## Architecture overview

Models:
- `apps/coin/models.py`:
  - `CoinEvent` (immutable event header)
  - `CoinLedgerEntry` (immutable double-entry rows)
  - `MonthlyCoinSnapshot` (immutable hash record)
  - `CoinAccount` (user/system accounts, status)
- `apps/payments/models.py`:
  - `PaymentEvent` (verified provider event, links to mint)

Services:
- `apps/coin/services/ledger.py`:
  - `_validate_entries(...)` enforces balance + account existence + status + system whitelist
  - `post_event_and_entries(...)` is the canonical write path
  - `create_transfer(...)`, `create_spend(...)`, `mint_for_payment(...)`
- `apps/coin/services/payments.py`:
  - `mint_from_payment_event(...)` – internal-only wrapper
- `apps/coin/services/snapshot.py`:
  - `generate_monthly_coin_snapshot(...)` – deterministic ordering + hashing

Commands:
- `apps/coin/management/commands/coin_invariant_check.py`
- `apps/coin/management/commands/coin_backfill_accounts.py`
- `apps/payments/management/commands/coin_payment_audit.py`
- `apps/coin/management/commands/coin_snapshot_month.py`

## Immutability guarantees
- `CoinEvent.save/delete` and `CoinLedgerEntry.save/delete` raise `ValidationError` on updates/deletes.
  - See `apps/coin/models.py`.

## Double-entry balance
- `_validate_entries(...)` sums debits/credits and rejects unbalanced postings.
  - See `apps/coin/services/ledger.py`.
- `coin_invariant_check` revalidates balance grouped by `event_id`.

## System account whitelist
- Allowed system accounts are defined in `SYSTEM_ACCOUNT_KEYS` in `apps/coin/models.py`.
- `_validate_entries(...)` rejects unknown system accounts (no `system:*` wildcard).
Allowed keys and purpose:
- `system:fees` — transfer fee sink
- `system:revenue` — spend sink for internal goods/services
- `system:mint` — mint counterparty for payment → SLC

## Mint security boundaries
- No public mint endpoints exist in `apps/coin/urls.py`.
- Stripe webhook verification happens in `apps/payments/webhook.py` via `apps/payments/clients/stripe.py`.
- Minting is only allowed with a `PaymentEvent` (`mint_for_payment(...)` in `apps/coin/services/ledger.py`).
- `post_event_and_entries(...)` rejects mint events without a matching `PaymentEvent`.

## Rate limiting and abuse control
- Transfer/spend endpoints use throttle scopes in `apps/coin/views.py`.
- Rates are configured in `core/settings/base.py`.

## Deterministic snapshots
- `generate_monthly_coin_snapshot(...)` orders rows by `(created_at, id)` and hashes a canonical JSON row set.
- Hashes are stored in `MonthlyCoinSnapshot`.

## CI/verification suggestions
- Run: `python manage.py test apps.coin`
- Run: `python manage.py test tests.test_payments_webhook_coin`
- Run: `python manage.py coin_invariant_check` (or `make coin-invariant-check`)
- Run: `pytest apps/coin/tests` (coin tests are pytest-based)

## Where bugs typically occur
- Account key mismatch (`user:<id>` vs stored account_key)
- System account whitelist mismatch
- Idempotency collisions on `{provider}:{event_id}`
- Cursor changes (treat `next_cursor` as opaque)
- PaymentEvent state transitions (received → minted)
