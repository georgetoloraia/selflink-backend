# Gift Effects Contract (Mobile UI)

This document defines the optional `effects` field on `GiftType`. The backend **stores and returns** effects but does not interpret them.

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

## effects structure

```json
{
  "version": 1,
  "persist": { "mode": "none" | "window", "window_seconds": 3600 },
  "effects": [
    { "type": "burst", "style": "lottie" },
    { "type": "border_glow", "color": "#FFD166", "intensity": 0.8 },
    { "type": "highlight", "color": "#FF4D6D" },
    { "type": "badge", "text": "Super Like" }
  ]
}
```

### Supported types (v1)
- `burst` — one‑time animation (e.g., Lottie).
- `border_glow` — persistent glow/border effect.
- `highlight` — persistent highlight around the item.
- `badge` — persistent badge UI.

### Persistence
- `persist.mode = "none"` → effect is a burst only.
- `persist.mode = "window"` + `window_seconds` → persist until window expires.

## Notes
- `effects` is always returned (default `{}`).
- Effects are optional; clients should treat unknown types as no‑ops.
- Media URLs are absolute (preferred).
