# Gifts Admin Checklist (60 seconds)

Use this to add a GiftType quickly and safely.

## 60‑second checklist
1) **Admin → GiftType → Add**
2) Fill:
   - `key` (unique, lowercase, e.g. `sparkles_049`)
   - `name`
   - `kind` (`static` or `animated`)
   - `price_slc_cents` (SLC cents; 100 = $1.00)
   - `is_active` (checked)
3) Media:
   - Upload `media_file` (PNG recommended) **or** set `media_url`.
   - If animated, upload `animation_file` (Lottie JSON) **or** set `animation_url`.
   - Always keep a **media_url/media_file** fallback even for animated gifts.
4) Effects (optional): paste Effects v2 JSON.
5) Save.
6) Verify: `GET /api/v1/payments/gifts/` includes the gift.

---

## Static vs Animated
- **Static**: `kind=static`, `media_url` only.
- **Animated**: `kind=animated`, `animation_url` (Lottie JSON) + `media_url` fallback.

---

## Pricing
- `price_slc_cents` uses SLC cents.
- 1 SLC == $1.00 → `100` cents.
- Examples: $0.49 → `49`, $1.99 → `199`.

---

## Effects v2 (allowed types)
Supported types: `overlay`, `border_glow`, `highlight`, `badge`.

**Overlay example**
```json
{
  "version": 2,
  "persist": { "mode": "window", "window_seconds": 3600 },
  "effects": [
    { "type": "overlay", "scope": "post", "animation": "/media/gifts/trendy/spotlight.json" }
  ]
}
```

---

## Troubleshooting
- Gift not visible: `is_active` must be true; catalog returns active gifts only.
- Animation not playing: verify the Lottie JSON URL is reachable.
- Effects not visible: effect types must be in the allowed list.
- Deleting gifts fails: set `is_active=false` (soft delete).
