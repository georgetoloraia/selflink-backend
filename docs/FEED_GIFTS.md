# Feed Gifts + Paid Likes (SLC Spend)

This document describes how “paid reactions” (gifts) work for feed posts and comments, how they map to SLC spends, and the exact response contract for rendering in clients.

Verified from code:
- Post gifts endpoint: `apps/social/views.py:PostViewSet.gifts`
- Comment gifts endpoint: `apps/social/views.py:CommentViewSet.gifts`
- Gift rendering fields: `apps/social/serializers.py:PostSerializer.get_recent_gifts`, `CommentSerializer.get_recent_gifts`
- PaidReaction payload: `apps/social/serializers.py:PaidReactionSerializer`
- Gift type fields: `apps/payments/models.py:GiftType`, `apps/payments/serializers.py:GiftTypeSerializer`
- Coin spend metadata: `apps/coin/services/ledger.py:create_spend`

## Overview

- A **paid reaction** is a SLC spend tied to a `GiftType`, attached to a post or a comment.
- Paid reactions are **not** free likes. Likes are separate endpoints (see “Likes” below).
- The spend is recorded in the coin ledger with a deterministic `reference`.

## Endpoints

### Gift catalog (read‑only)

```
GET /api/v1/payments/gifts/
```

Returns `GiftType` objects used by clients to render gifts.
Only `is_active=true` gifts are returned.

### Send gift to a post

```
POST /api/v1/posts/{post_id}/gifts/
```

Body:
```json
{
  "gift_type_id": 123,
  "quantity": 2,
  "note": "optional note"
}
```

Headers (optional but recommended):
```
Idempotency-Key: <uuid>
```

### Send gift to a comment

```
POST /api/v1/comments/{comment_id}/gifts/
```

Same payload and idempotency rules as post gifts.

### Likes (free)

```
POST /api/v1/posts/{post_id}/like/
POST /api/v1/posts/{post_id}/unlike/
POST /api/v1/comments/{comment_id}/like/
POST /api/v1/comments/{comment_id}/unlike/
```

These are **not** paid; they simply toggle a like and return `{liked, like_count}`.

## Rendering contract (authoritative)

### Post serializer gift field

`PostSerializer` exposes **only** `recent_gifts` (no `gift_summary` field exists).

Example: post with no gifts
```json
{
  "id": 10,
  "text": "hello",
  "like_count": 0,
  "viewer_has_liked": false,
  "recent_gifts": []
}
```

Example: post with gifts
```json
{
  "id": 10,
  "text": "hello",
  "like_count": 2,
  "viewer_has_liked": true,
  "recent_gifts": [
    {
      "id": 501,
      "sender_id": 99,
      "target_type": "post",
      "post": 10,
      "comment": null,
      "gift_type": {
        "id": 7,
        "key": "rose",
        "name": "Rose",
        "kind": "static",
        "price_cents": 100,
        "price_slc_cents": 100,
        "art_url": "",
        "media_url": "https://cdn.example/gifts/rose.png",
        "animation_url": "",
        "is_active": true,
        "metadata": {}
      },
      "quantity": 2,
      "total_amount_cents": 200,
      "created_at": "2026-01-24T12:00:00Z",
      "idempotency_key": "2f5d2c2d-3a9a-4b7d-9f68-ef2df3e3f6f6"
    }
  ]
}
```

### Comment serializer gift field

`CommentSerializer` also exposes only `recent_gifts`.

Example: comment with gifts
```json
{
  "id": 200,
  "text": "nice",
  "like_count": 1,
  "viewer_has_liked": false,
  "recent_gifts": [/* PaidReaction objects as above */]
}
```

## Gift type fields (what clients can render)

Gift types come from:

- `apps/payments/models.py:GiftType`
- `apps/payments/serializers.py:GiftTypeSerializer`

Fields exposed:
`id`, `key`, `name`, `kind`, `price_cents`, `price_slc_cents`, `art_url`, `media_url`, `animation_url`, `is_active`, `metadata`.

`kind` is `static` or `animated`. Clients choose which URL to render based on `kind`:
- `static`: prefer `media_url` (or `art_url` if used by your storage).
- `animated`: prefer `animation_url`.

## Coin spend reference + ledger visibility

Gift spends use deterministic references (stored in `CoinEvent.metadata.reference`):

- Post gifts: `gift:post:<post_id>:<gift_type_key_or_id>`
- Comment gifts: `gift:comment:<comment_id>:<gift_type_key_or_id>`

These spends appear in:
```
GET /api/v1/coin/ledger/
```

Look for `event_metadata.reference` on the spend entry.

## Idempotency rules

Gift endpoints accept `Idempotency-Key` (UUID recommended):

- Same key + identical payload (same target, gift_type, quantity) → **no double spend**.
- Same key + different payload → **400** `{detail, code: "idempotency_conflict"}`.

## Rate limits

Gift creation is throttled under the `paid_reaction` scope.
Set `PAID_REACTION_THROTTLE` in env (see `core/settings/base.py`).

## Errors (gift endpoints)

| Status | Code | When |
| --- | --- | --- |
| 400 | `invalid_quantity` | quantity < 1 or > 50 |
| 404 | `invalid_gift_type` | gift_type_id not found |
| 400 | `gift_inactive` | gift_type exists but is inactive |
| 400 | `invalid_amount` | computed total <= 0 |
| 400 | `insufficient_funds` | user has not enough SLC |
| 400 | `account_inactive` | user coin account not active |
| 400 | `account_invalid` | invalid coin account state |
| 400 | `idempotency_conflict` | same key, different payload |

## QA checklist (contributor)

1) Create two users.
2) Mint SLC to sender (admin, or via payment webhook).
3) `POST /api/v1/posts/{id}/gifts/` → expect 201, balance drops.
4) Repeat with same Idempotency-Key → expect 200, no extra spend.
5) Check `/api/v1/coin/ledger/` for `reference` metadata.
6) Test comment gifts: `/api/v1/comments/{id}/gifts/`.
7) Try invalid GiftType → 404 with `invalid_gift_type`.
