# BTCPay Server (Bitcoin/Lightning) integration

This doc describes how BTCPay integrates with the existing `PaymentEvent` → SLC mint flow.
No public mint endpoints are exposed; minting happens only after verified webhooks.

## Required env vars
- `BTCPAY_BASE_URL`
- `BTCPAY_API_KEY`
- `BTCPAY_STORE_ID`
- `BTCPAY_WEBHOOK_SECRET`
- `BTCPAY_SIGNATURE_HEADER` (optional; default `HTTP_BTCPAY_SIG`)
- `BTCPAY_ALLOWED_CURRENCIES` (default `USD,EUR`)
- `BTCPAY_PAID_STATUSES` (default `settled,paid`)
- `BTCPAY_FAILED_STATUSES` (default `expired,invalid`)
- `BTCPAY_AMOUNT_IN_CENTS` (optional; default `false`)
- `BTCPAY_TIMEOUT_SECONDS` (default `10`)

## End-to-end flow
1) Client requests a checkout:
   - `POST /api/v1/payments/btcpay/checkout/`
   - Body: `{ "amount_cents": 1500, "currency": "USD" }`
   - Response includes `reference`, `amount_cents`, `currency`, `payment_url`.
2) Client opens `payment_url` (BTCPay invoice checkout).
3) BTCPay sends a webhook to:
   - `POST /api/v1/payments/btcpay/webhook/`
4) Webhook verifies signature, fetches invoice details from BTCPay,
   creates a `PaymentEvent`, and mints SLC only when the invoice is settled/paid.

## Reference binding
- The backend stores a `PaymentCheckout` row for every SLC purchase attempt.
- The checkout `reference` is stored with the BTCPay invoice metadata.
- Webhook resolves the user via `PaymentCheckout` (not via client metadata).

## Idempotency and safety
- Provider invoice id is the idempotency key: `btcpay:invoice_id`.
- Webhook retries do not double-mint.
- Minting requires `PaymentEvent.verified_at` and a final paid status.
- Amount/currency mismatches against the stored checkout are rejected.

## Replay and auditing
- Use BTCPay webhook replay; events are safe to resend.
- Audit commands:
  - `python manage.py coin_payment_audit --provider btcpay --show`
  - `python manage.py coin_invariant_check`

## Files to review
- Provider client: `apps/payments/providers/btcpay.py`
- Checkout view: `apps/payments/btcpay.py`
- Webhook: `apps/payments/webhooks/btcpay_webhook.py`
- Payment models: `apps/payments/models.py`
