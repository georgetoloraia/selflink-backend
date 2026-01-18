# SelfLink Gifts

This document explains how Gifts work today, how to add new GiftType entries, and how pricing relates to SLC.
It is docs-only and does not change any backend behavior.

## Overview

There are two related concepts:
- GiftType: the catalog entry (name, price, artwork).
  Verified from code: `apps/payments/models.py: GiftType`.
- Gift: a sent gift instance from one user to another.
  Verified from code: `apps/social/models.py: Gift`.

GiftType entries are exposed for the mobile app to render a gift catalog. Gift instances are created via the social API.

## Current behavior (verified)

GiftType catalog
- Endpoint: `GET /api/v1/payments/gifts/`.
  Verified from code: `apps/payments/urls.py` (router `payments/gifts`) and `apps/payments/views.py: GiftTypeViewSet`.
- Response fields: `id`, `name`, `price_cents`, `art_url`, `metadata`.
  Verified from code: `apps/payments/serializers.py: GiftTypeSerializer`.
- Ordering: ascending by `price_cents`.
  Verified from code: `apps/payments/models.py: GiftType.Meta.ordering`.
- If payments are disabled, the list returns an empty array (HTTP 200).
  Verified from code: `apps/payments/views.py: GiftTypeViewSet.list` and `apps/payments/feature_flag.py: payments_enabled`.

Gift sending
- Endpoint: `POST /api/v1/gifts/` (authenticated).
  Verified from code: `apps/social/urls.py` (router `gifts`) and `apps/social/views.py: GiftViewSet`.
- Payload fields: `receiver`, `gift_type`, `payload`.
  Verified from code: `apps/social/serializers.py: GiftSerializer`.
- Current behavior: gift creation does not debit SLC or enforce pricing.
  Verified from code: `apps/social/serializers.py: GiftSerializer.create` and `apps/social/views.py: GiftViewSet.perform_create` (no SLC call).

## GiftType fields (what each does)

Verified from code: `apps/payments/models.py: GiftType`.
- `name` (string, unique) - display name.
- `price_cents` (positive integer) - price in cents (see SLC pricing below).
- `art_url` (URL string) - artwork URL, optional.
- `metadata` (JSON) - freeform metadata (optional).

## Static vs animated gifts

The backend does not enforce static vs animated. Use `metadata` to signal the type to clients.
Suggested convention (client-only, not enforced by backend):
- `metadata.type = "static"` or `"animated"`.

Verified from code: `apps/payments/models.py: GiftType.metadata` (JSON field, no validation).

## Media requirements and storage

The backend only stores a URL in `art_url`. It does not upload or validate media.
- Verified from code: `apps/payments/models.py: GiftType.art_url` (URLField).

Where that URL points depends on how you host media:
- Local/dev media can be served by Django or nginx in dev/infra setups.
  Verified from code: `core/urls.py` (media serving when `DEBUG` or `SERVE_MEDIA`).
  See also: `docs/WHY_THIS_STACK.md` (media via nginx) and `docs/RUNBOOK.md` (storage notes).
- Production media is typically served from S3/MinIO or a CDN.
  Verified from docs: `docs/RUNBOOK.md` (storage envs and guidance).

For specific media specs (dimensions, formats), see `docs/GIFTS_MEDIA_SPEC.md`.

## Pricing in SLC (current vs planned)

Current state
- GiftType has a `price_cents` field, but no SLC spend is enforced when creating a Gift.
  Verified from code: `apps/payments/models.py: GiftType.price_cents` and `apps/social/serializers.py: GiftSerializer.create`.

Planned integration (not implemented yet)
- Gifts should eventually call the SLC spend flow:
  - `POST /api/v1/coin/spend/` expects `amount_cents` and a `reference` string.
    Verified from code: `apps/coin/views.py: CoinSpendView`.
  - The ledger creates a `spend` event with a `reference` field.
    Verified from code: `apps/coin/services/ledger.py: create_spend`.
- Suggested (not enforced) reference pattern: `gift:<gift_type_id>`.

For SLC pricing details, see `docs/GIFTS_SLC_PRICING.md`.

## Admin workflow (no code changes)

There is no public API for creating GiftType entries (read-only list only).
Verified from code: `apps/payments/views.py: GiftTypeViewSet` (ReadOnlyModelViewSet).
The verified ways to add gifts without code changes are:

Option A: Django shell
```bash
python manage.py shell
```
```python
from apps.payments.models import GiftType
GiftType.objects.create(
    name="Rose",
    price_cents=100,
    art_url="https://cdn.example.com/gifts/rose.webp",
    metadata={"type": "static", "description": "Classic rose"},
)
```

Option B: Seed demo data (dev only)
```bash
python manage.py seed_demo
```
This seeds two example gifts: "Starlight" and "Aurora".
Verified from code: `apps/core/management/commands/seed_demo.py: _ensure_gift_types`.

## 5-minute quickstart

1) Create a GiftType via shell (see above).
2) Verify the catalog:
   - `GET /api/v1/payments/gifts/`
3) Send a gift (no SLC debit yet):
   - `POST /api/v1/gifts/` with `receiver`, `gift_type`, `payload`.

## Troubleshooting

- Gift catalog is empty:
  - Payments feature is disabled. Enable `FEATURE_FLAGS["payments"]`.
  - Verified from code: `apps/payments/views.py: GiftTypeViewSet.list` and `apps/payments/feature_flag.py: payments_enabled`.
- Media does not load:
  - `art_url` points to a URL that is not reachable. Confirm CDN/S3/media hosting.
  - Verified from code: `apps/payments/models.py: GiftType.art_url` (URL only, no upload).
- Gift creation works but no SLC balance changes:
  - This is expected today; SLC spend is not wired to Gift creation.
  - Verified from code: `apps/social/serializers.py: GiftSerializer.create`.

## Current state vs future work

Current state (implemented)
- Gift catalog via `/api/v1/payments/gifts/` (read-only).
- Gift creation via `/api/v1/gifts/` (no SLC spend).

Future work (planned, not implemented)
- Enforce SLC spend when sending gifts.
- Use `CoinSpendView` with a consistent `reference` (e.g., `gift:<gift_type_id>`).
- Add validations for gift pricing and media types.
