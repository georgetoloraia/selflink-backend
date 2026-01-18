# Gift Pricing in SLC (SelfLink Coin)

This document explains how GiftType pricing maps to SLC today and how gifting is expected to integrate with the SLC spend flow.

## What exists today (verified)
- GiftType has a `price_cents` field (positive integer).
  Verified from code: `apps/payments/models.py: GiftType.price_cents`.
- SLC is pegged 1:1 to USD and uses integer cents only.
  Verified from docs: `docs/coin/WALLET.md`.

Implication:
- `price_cents` is already in the same unit as SLC cents.
- Example: `price_cents = 150` means 1.50 SLC (i.e., 150 cents).

## What is NOT implemented yet
- Sending a Gift does not debit SLC.
  Verified from code: `apps/social/serializers.py: GiftSerializer.create` and `apps/social/views.py: GiftViewSet.perform_create`.
- There is no server-side validation that the sender has enough SLC for a gift.

## Planned integration (no code yet)

Use the existing SLC spend endpoint as the charging mechanism:
- `POST /api/v1/coin/spend/` expects `amount_cents` and `reference`.
  Verified from code: `apps/coin/views.py: CoinSpendView`.
- The ledger writes a `spend` event using `reference` for audit trails.
  Verified from code: `apps/coin/services/ledger.py: create_spend`.

Suggested (not enforced) reference format for gifts:
- `gift:<gift_type_id>`

This keeps gift pricing auditable in the append-only ledger (spend debit + system revenue credit).
Verified from docs: `docs/coin/TECHNICAL_REVIEW.md` (spend uses `system:revenue`).

## Accounting and audit notes
- SLC ledger is append-only and double-entry.
  Verified from docs: `docs/coin/TECHNICAL_REVIEW.md`.
- The `coin_invariant_check` command validates balanced postings.
  Verified from code: `apps/coin/management/commands/coin_invariant_check.py`.
