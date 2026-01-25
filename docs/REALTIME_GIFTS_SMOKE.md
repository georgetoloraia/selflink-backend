# Realtime Gifts — E2E Smoke Test

This is a 5–10 minute checklist to validate “gift.received” realtime events end‑to‑end.

## Prereqs

- Backend + realtime services running
- `REALTIME_PUBLISH_URL` points to the realtime service (e.g. `http://localhost:8002`)
- `REALTIME_PUBLISH_TOKEN` set on both backend and realtime service
- Payments feature flag enabled (`FEATURE_PAYMENTS=true`)

## Steps

1) **Create / login two users**
   - User A (sender) and User B (viewer).

2) **Seed or verify a gift exists**
   - Confirm `test_heart_1usd` exists via:
     - `GET /api/v1/payments/gifts/`

3) **Open the same post**
   - User A and User B open the same post screen.

4) **Connect realtime on User B**
   - WebSocket:
     ```
     ws://<realtime-host>/ws?token=<jwt>&channels=post:<post_id>
     ```

5) **Send a gift from User A**
   - `POST /api/v1/posts/{post_id}/gifts/`
   - Include `Idempotency-Key` header.

6) **Confirm User B receives a `gift.received` event**
   - Check WS payload has the expected fields and `target.id == post_id`.

7) **Refresh the post**
   - Confirm `recent_gifts` now includes the gift.

## Troubleshooting

**No realtime burst**
- Check WS connection and token.
- Check backend logs for `gift_realtime.publish_*` markers.
- Confirm `REALTIME_PUBLISH_TOKEN` matches between backend and realtime service.
- If using rate limit, check `REALTIME_PUBLISH_RATE_LIMIT`.

**Gift send fails**
- Ensure sender has SLC.
- Ensure gift is active.
- Ensure `Idempotency-Key` is provided.

**No catalog**
- Ensure `FEATURE_PAYMENTS=true`.
