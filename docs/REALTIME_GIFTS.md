# Realtime Gift Events

This document describes the realtime event emitted when a paid gift is sent, so the client can trigger an immediate burst/animation without waiting for a feed refresh.

Verified from code:
- Gift send endpoints: `apps/social/views.py:PostViewSet.gifts`, `CommentViewSet.gifts`
- Publish helper: `apps/social/events.py:publish_gift_received`
- Realtime pubsub: `apps/core/pubsub.py:publish_event`
- Realtime WS subscription: `services/realtime/app.py` (`channels` query param)

## Event contract

**Event type:** `gift.received`

Payload shape:
```json
{
  "type": "gift.received",
  "id": 12345,
  "target": { "type": "post", "id": 777 },
  "sender": { "id": 42 },
  "gift_type": {
    "id": 7,
    "key": "test_heart_1usd",
    "name": "Test Heart",
    "kind": "static",
    "media_url": "https://your.host/media/gifts/test-heart.png",
    "animation_url": "",
    "price_slc_cents": 100,
    "is_active": true
  },
  "quantity": 2,
  "total_amount_cents": 200,
  "created_at": "2026-01-25T10:15:30Z"
}
```

## Channels

The backend publishes to **target‑scoped channels**:

- `post:{post_id}`
- `comment:{comment_id}`

Clients should subscribe to the channel matching the item they’re viewing.

## When it fires

The event is published only **after**:
1) SLC spend succeeds, and
2) `PaidReaction` row is created, and
3) the DB transaction commits (`transaction.on_commit`).

If publish fails (Redis/realtime down), the gift still succeeds. Emission is **best‑effort**.

## How to subscribe (WS)

Realtime WebSocket supports `channels` query param:

```
ws://<realtime-host>/ws?token=<jwt>&channels=post:123,comment:456
```

## Local testing

1) Connect a WebSocket client with `channels=post:<id>`.
2) Send a gift to that post.
3) Verify you receive a `gift.received` event on the socket.
