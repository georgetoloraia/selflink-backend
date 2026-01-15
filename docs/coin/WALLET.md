# SLC Wallet (SelfLink Coin)

SLC is an internal, off-chain credit system pegged 1:1 to USD (integer cents only).
It is not a blockchain token and has no withdrawals or on-chain representation.

## Core flows

1) Payment → SLC mint
- Stripe webhook verifies signatures in `apps/payments/webhook.py`.
- A `PaymentEvent` is created in `apps/payments/models.py`.
- `PaymentEvent` is marked verified after signature validation; minting requires verified events.
- Mint amount is derived from Stripe amounts (`amount_total`/`amount_received`), not metadata.
- Minting uses `apps/coin/services/payments.py` → `mint_for_payment(...)`.
- Mint postings are double-entry against `system:mint` in `apps/coin/services/ledger.py`.
- Idempotency key is `{provider}:{provider_event_id}`; replays do not double-mint.

2) P2P transfer
- Endpoint: `POST /api/v1/coin/transfer/` in `apps/coin/views.py`.
- Posts sender debit + receiver credit + fee credit to `system:fees`.
- Fee is `COIN_FEE_BPS` with `COIN_FEE_MIN_CENTS`.

3) Spend on internal goods/services
- Endpoint: `POST /api/v1/coin/spend/` in `apps/coin/views.py`.
- Posts user debit + credit to `system:revenue`.

System accounts are limited to `system:fees`, `system:revenue`, and `system:mint`.

## Idempotency + replay behavior
- Stripe events are safe to replay; duplicates are detected by `PaymentEvent.provider_event_id`.
- Mints are guarded by `CoinEvent.idempotency_key` and `PaymentEvent.minted_coin_event`.

## Operational commands
- Audit payment events: `python manage.py coin_payment_audit --show`
- Check invariants (CI-safe, read-only): `python manage.py coin_invariant_check`
- Backfill user accounts (if migrating existing DBs): `python manage.py coin_backfill_accounts --batch-size 1000`

## Safe rollout sequence
- Fresh deploy: migrations create system accounts; new users get a `CoinAccount` via `apps/users/signals.py`.
- Existing DB: deploy code + migrations, then run `coin_backfill_accounts` once.

## Replaying Stripe events safely
- Stripe Dashboard: Developers → Events → select event → “Resend” to the webhook endpoint.
- Stripe CLI (local): `stripe listen --forward-to http://localhost:8000/api/v1/payments/stripe/webhook/`
  then `stripe events resend <event_id>` (or `stripe trigger payment_intent.succeeded` for test data).
- Idempotency: `PaymentEvent.provider_event_id` and `CoinEvent.idempotency_key` ensure replays mint at most once.

## Auditing unminted PaymentEvents
Run: `python manage.py coin_payment_audit --show`
- `unminted_events=N` means verified provider events are stored but not minted yet.
- `mint_events_without_payment_event` should be `0` in a healthy system.

## Mint provenance invariant
- `coin_invariant_check` enforces that every mint is linked to a verified `PaymentEvent`.

## Troubleshooting
- Signature failures: webhook returns 400 and logs a rejection in `apps/payments/webhook.py`.
- Missing PaymentEvent: mint is rejected (no public mint endpoint).
- Suspended accounts: postings are blocked in `apps/coin/services/ledger.py`.

## Pagination
`/api/v1/coin/ledger/` uses an opaque cursor (`next_cursor`), ordered by `(created_at, id)`.
Treat the cursor as an opaque string; it is base64url JSON (`{"ts": "...", "id": ...}`) and legacy numeric cursors are accepted.
