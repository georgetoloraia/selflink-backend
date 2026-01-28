# Gift Effects Contract (Mobile UI)

This document defines the optional `effects` field on `GiftType`. The backend **stores and returns** effects but does not interpret them. Mobile renders only a small, supported set.

## GiftType fields (mobile‑relevant)

- `id`
- `key`
- `name`
- `kind` (`static` | `animated`)
- `media_url`
- `animation_url`
- `price_slc_cents`
- `is_active`
- `effects`

## Effects v2 structure (strict)

```json
{
  "version": 2,
  "persist": { "mode": "none" | "window", "window_seconds": 3600 },
  "effects": [
    { "type": "overlay", "scope": "post", "animation": "/media/gifts/snowfall.json", "clip_to_bounds": true },
    { "type": "border_glow", "color": "#FFD166", "intensity": 0.8 },
    { "type": "highlight", "color": "#FF4D6D" },
    { "type": "badge", "text": "Super Like" }
  ]
}
```

### Supported types (v1)
- `overlay` — Lottie overlay rendered inside post/comment (requires `animation`).
- `border_glow` — persistent glow/border effect.
- `highlight` — persistent highlight around the item.
- `badge` — persistent badge UI.

### Persistence
- `persist.mode = "none"` → effect is a burst only.
- `persist.mode = "window"` + `window_seconds` → persist until window expires.

## Validation
- Admin and API reject unsupported `type` values.
- `overlay` requires a non‑empty `animation` path/URL.
- Unknown keys are ignored by the client.

## Notes
- `effects` is always returned (default `{version: 2, effects: [], persist: {…}}`).
- Media URLs can be absolute or relative (e.g., `/media/...`).
- Realtime `gift.received` now includes full `gift_type` with normalized effects and may include `expires_at` for windowed effects.

## Presets (examples)
- Snowfall: `apps/payments/fixtures/gift_effects/snowfall_in_post_v2.json`
- Super Like: `apps/payments/fixtures/gift_effects/super_like_v2.json`
- Basic highlight: `apps/payments/fixtures/gift_effects/basic_highlight_v2.json`

## Snowfall asset
- Lottie file: `apps/payments/static/gifts/snowfall.json` → `/static/gifts/snowfall.json`
- Seed command: `python manage.py seed_gift_types` (creates/updates `winter_snow`)
