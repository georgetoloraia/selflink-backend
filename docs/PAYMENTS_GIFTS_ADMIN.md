## GiftType Admin Guide (60‑second setup)

GiftType drives the gift catalog (`GET /api/v1/payments/gifts/`) and paid gifts on posts/comments.
Mobile reads GiftType fields and renders media + effects.

### 60‑second checklist
1) **Admin → GiftType → Add**
2) Fill:
   - `key` (unique, lowercase, e.g. `super_like`)
   - `name` (display name)
   - `kind` (`static` or `animated`)
   - `price_slc_cents` (SLC cents; 100 = $1)
   - `is_active` (checked)
3) Media:
   - **Upload** `media_file` (PNG recommended) **or** set `media_url`
   - **Optional**: upload `animation_file` (Lottie JSON) **or** set `animation_url`
   - Always provide a **media_url/media_file** fallback even for animated gifts
4) Paste **effects JSON** (optional, v2 schema below)
5) Save
6) Verify:
   - `GET /api/v1/payments/gifts/` includes the gift

Realtime note:
- `gift.received` includes full `gift_type` with normalized effects.
- If `PUBLIC_BASE_URL` is set, realtime URLs are absolute; otherwise relative.

---

## Fields used by mobile

These must be present in the API response:
- `id`
- `key`
- `name`
- `kind`
- `media_url`
- `animation_url`
- `price_slc_cents`
- `is_active`
- `effects`

---

## Media requirements

- **media_url / media_file**: PNG or WebP, 256–512px square recommended.
- **animation_url / animation_file**: Lottie JSON (optional).
- Keep asset sizes reasonable (< 500KB if possible).
- If using relative paths, use `/media/...` or `/static/...` depending on storage.

---

## Effects v2 (allowed types only)

Supported `type` values:
- `overlay` (Lottie overlay)
- `border_glow`
- `highlight`
- `badge`

**Rules**
- `overlay` must include `animation` (URL or relative path).
- Unknown types are rejected by backend validation.

### Minimal templates (copy/paste)

**1) Static gift (no effects)**
```json
{
  "version": 2,
  "persist": { "mode": "none", "window_seconds": 0 },
  "effects": []
}
```

**2) Static with border glow**
```json
{
  "version": 2,
  "persist": { "mode": "window", "window_seconds": 3600 },
  "effects": [
    { "type": "border_glow", "color": "#FFD166", "intensity": 0.8 }
  ]
}
```

**3) Animated with overlay**
```json
{
  "version": 2,
  "persist": { "mode": "window", "window_seconds": 30 },
  "effects": [
    {
      "type": "overlay",
      "scope": "post",
      "clip_to_bounds": true,
      "z_index": 5,
      "opacity": 0.9,
      "animation": "/static/gifts/super-like.json",
      "fit": "cover",
      "loop": true,
      "duration_ms": 12000
    }
  ]
}
```

**4) Super Like (highlight + badge)**
```json
{
  "version": 2,
  "persist": { "mode": "window", "window_seconds": 86400 },
  "effects": [
    { "type": "highlight", "color": "#FF4D6D" },
    { "type": "badge", "text": "Super Like" }
  ]
}
```

---

## Pricing (SLC)

- `price_slc_cents` is in **SLC cents**
- **100 = 1 SLC** (1 USD equivalent by convention)

---

## Troubleshooting

- **Gift not in catalog**: ensure `is_active=true`. Catalog filters inactive gifts.
- **Animation not showing**: confirm `animation_url` is valid and accessible; ensure Lottie JSON is correct.
- **Effects not showing**: check `effects` JSON matches allowed types; invalid types are rejected.
- **Mobile crash**: keep effect types to the allowed set; always include `media_url` fallback.
