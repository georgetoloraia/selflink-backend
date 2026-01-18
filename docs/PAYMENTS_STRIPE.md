# Stripe Checkout (SLC purchases)

This integration uses Stripe Checkout Sessions (one-time payments) to buy SLC.
Minting happens only after verified Stripe webhooks create a `PaymentEvent`.

## Required env vars
- `STRIPE_API_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_ALLOWED_CURRENCIES` (default `USD,EUR,GEL`)
- `STRIPE_CHECKOUT_MIN_CENTS` (default `50`)
- `STRIPE_CHECKOUT_SUCCESS_URL`
- `STRIPE_CHECKOUT_CANCEL_URL`

## Checkout flow
1) Create a checkout reference:
   - `POST /api/v1/payments/stripe/checkout/`
   - Body: `{ "amount_cents": 1500, "currency": "USD" }`
2) Client redirects to `payment_url`.
3) Stripe calls webhook:
   - `POST /api/v1/payments/stripe/webhook/`
4) Webhook verifies signature, loads `PaymentCheckout` by reference, creates `PaymentEvent`,
   and mints SLC if `payment_status == "paid"`.

## Reference binding
- The backend stores a `PaymentCheckout` row for every SLC purchase attempt.
- Stripe Checkout uses `client_reference_id` (and metadata) to include this reference.
- Webhook **does not trust user_id from metadata**; it resolves the user via `PaymentCheckout`.

## Replay and auditing
- Stripe can retry events; idempotency is enforced by `provider_event_id`.
- Safe to replay webhook events.
- Audit commands:
  - `python manage.py coin_payment_audit --provider stripe --show`
  - `python manage.py coin_invariant_check`
