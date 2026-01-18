# iPay (Bank of Georgia) integration

This doc describes how iPay integrates with the existing `PaymentEvent` → SLC mint flow.
No public mint endpoints are exposed; minting happens only after verified webhooks.

## Required env vars
- `IPAY_WEBHOOK_SECRET` (required): shared secret used to verify webhook signatures.
- `IPAY_SIGNATURE_HEADER` (optional): request header containing signature, default `HTTP_X_IPAY_SIGNATURE`.
- `IPAY_ALLOWED_CURRENCIES` (optional): comma list (default `USD,EUR,GEL`).
- `IPAY_PAID_STATUSES` (optional): comma list of paid statuses (default `paid,success,completed`).
- `IPAY_FAILED_STATUSES` (optional): comma list of failed statuses (default `failed,canceled,expired`).
- `IPAY_AMOUNT_IN_CENTS` (optional): `true` if amounts are already in cents (default `true`).
- `IPAY_FIELD_EVENT_ID`, `IPAY_FIELD_REFERENCE`, `IPAY_FIELD_STATUS`,
  `IPAY_FIELD_AMOUNT`, `IPAY_FIELD_CURRENCY` (optional overrides for payload keys).

## End-to-end flow
1) Client requests a checkout reference:
   - `POST /api/v1/payments/ipay/checkout/`
   - Response includes `reference`, `amount_cents`, `currency`.
2) Client redirects to iPay with the reference (order id) and amount.
3) iPay sends a webhook to:
   - `POST /api/v1/payments/ipay/webhook/`
4) Webhook verifies signature, parses authoritative amount + currency,
   creates a `PaymentEvent`, and mints SLC if the status is paid.

## Idempotency and safety
- Provider event id is used as idempotency key: `provider:event_id`.
- Replayed webhooks do not double-mint.
- Minting requires `PaymentEvent.verified_at` and a paid status.
- Amount/currency mismatches against the stored checkout reference are rejected.

## Replay and auditing
- If iPay supports replay, resend the same event; it is safe and idempotent.
- Audit with:
  - `python manage.py coin_payment_audit --provider ipay --show`
  - `python manage.py coin_invariant_check`

## Files to review
- Webhook: `apps/payments/webhooks/ipay_webhook.py`
- Provider parser/verifier: `apps/payments/providers/ipay.py`
- PaymentEvent + checkout model: `apps/payments/models.py`
