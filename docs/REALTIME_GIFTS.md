# Realtime Gifts (Backend)

This document describes the realtime event emitted when a paid gift is sent.

## Event

- **Type:** `gift.received`
- **Channels (strict):**
  - `post:{post_id}`
  - `comment:{comment_id}`
  - `post`/`comment` IDs must be positive integers.

### Payload

```json
{
  "type": "gift.received",
  "id": 123,
  "target": { "type": "post", "id": 456 },
  "sender": { "id": 42 },
  "gift_type": {
    "id": 7,
    "key": "test_heart_1usd",
    "name": "Test Heart",
    "kind": "static",
    "media_url": "https://api.example.com/media/gifts/test-heart.png",
    "animation_url": "",
    "price_slc_cents": 100,
    "is_active": true
  },
  "quantity": 1,
  "total_amount_cents": 100,
  "created_at": "2025-01-25T12:00:00Z"
}
```

## Emit timing

- Emitted **after** SLC spend succeeds and **after** `PaidReaction` is created.
- Uses `transaction.on_commit` to ensure the DB commit has completed.
- Best‑effort: failures to publish do **not** block the gift transaction.

## Publish path

1) Django calls `apps.realtime.publish.publish_realtime_event`.
2) If `REALTIME_PUBLISH_URL` is configured, it sends:
   - `POST {REALTIME_PUBLISH_URL}/internal/publish`
   - Body: `{ "channel": "...", "payload": {...} }`
   - Header: `Authorization: Bearer <REALTIME_PUBLISH_TOKEN>` (**required**)
3) If HTTP publish fails, it falls back to Redis publish on `PUBSUB_REDIS_URL`.

### Internal endpoint security
- **Token is required** (`REALTIME_PUBLISH_TOKEN`).
- Rejects unknown channels and unknown event types.
- Recommended to keep the endpoint internal/private.

## Local testing

- Start realtime service (FastAPI) so `/internal/publish` is reachable.
- Use curl to simulate:

```bash
curl -X POST "http://localhost:8002/internal/publish" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <REALTIME_PUBLISH_TOKEN>" \
  -d '{"channel":"post:123","payload":{"type":"gift.received"}}'
```

- Connect a websocket client to:
  `ws://localhost:8001/ws?token=<jwt>&channels=post:123`

You should receive the payload immediately.
