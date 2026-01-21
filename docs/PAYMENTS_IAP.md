# IAP (Apple + Google) verification

This document describes the internal purchase verification flow for Apple and Google IAP.
Minting is internal-only and requires a verified `PaymentEvent`.

## Endpoint
`POST /api/v1/payments/iap/verify/` (authenticated)

Request body:
```json
{
  "platform": "ios",
  "product_id": "com.selflink.slc.499",
  "transaction_id": "tx_123",
  "receipt": "<base64>"
}
```
For Android:
```json
{
  "platform": "android",
  "product_id": "com.selflink.slc.499",
  "transaction_id": "order_123",
  "purchase_token": "<token>"
}
```

Response (success):
```json
{
  "received": true,
  "provider": "apple_iap",
  "provider_event_id": "tx_123",
  "coin_event_id": 123456,
  "balance_cents": 499,
  "currency": "USD"
}
```

Verified from code:
- Endpoint: `apps/payments/urls.py: payments/iap/verify/`
- View: `apps/payments/iap.py: IapVerifyView`
- Serializer: `apps/payments/serializers.py: IapVerifySerializer`

## SKU allowlist
- SKUs are allowlisted in `IAP_SKU_MAP`.
- Amounts/currency are derived from the allowlist, not from client input.
- Unknown SKUs are rejected.

Settings:
- `IAP_SKU_MAP` (JSON) — example in `infra/.env.example`.
- Defaults (if env is empty) are defined in `core/settings/base.py`.

## Provider verification
- Apple verification stub: `apps/payments/providers/iap/apple.py: verify_apple_receipt`.
- Google verification stub: `apps/payments/providers/iap/google.py: verify_google_purchase`.

These functions are structured for real verification calls and should be replaced with actual Apple/Google verification logic.
Until then, they raise a validation error unless mocked in tests.

## Idempotency and safety
- PaymentEvent is created with `(provider, provider_event_id)`.
- Replays return success without double-minting.
- Minting requires `PaymentEvent.verified_at` (`apps/coin/services/payments.py`).

## Provider toggles
- `PAYMENTS_PROVIDER_ENABLED_IAP=false` disables the endpoint with 403.
- Other providers are toggled similarly (Stripe/iPay/BTCPay).

## Troubleshooting
- 403: provider disabled or payments feature disabled.
- 400: unknown SKU, invalid receipt/token, or verification failure.
- 409: purchase not settled (verification result not in a paid state).

## Audit commands
- `python manage.py coin_payment_audit --provider apple_iap --show`
- `python manage.py coin_payment_audit --provider google_iap --show`
- `python manage.py coin_invariant_check`
