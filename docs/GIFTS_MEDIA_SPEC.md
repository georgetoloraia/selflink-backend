# Gift Media Spec (recommendations)

This spec is a set of recommended guidelines for Gift artwork.
The backend does not enforce or validate these rules; it only stores a URL.
Verified from code: `apps/payments/models.py: GiftType.art_url` (URLField, optional).

## Static gifts (recommended)
- Format: `webp` or `png`.
- Dimensions: 512x512 or 1024x1024 square.
- File size target: <= 500 KB (smaller for low-end devices).
- Alpha: allowed (transparent background is fine).

Example URLs (pick one):
- `https://cdn.example.com/gifts/rose.webp`
- `/media/gifts/rose.png`

## Animated gifts (recommended)
- Format: `webp` (animated) or `gif`.
- Dimensions: 512x512 or 1024x1024.
- Frame rate: <= 24 fps.
- File size target: <= 2 MB.

Example URLs:
- `https://cdn.example.com/gifts/fireworks.webp`
- `/media/gifts/fireworks.gif`

## URL and storage rules
- `art_url` must be a fully qualified URL or a reachable `/media/...` URL.
  Verified from code: `apps/payments/models.py: GiftType.art_url`.
- Media hosting depends on your storage setup:
  - Dev/local can serve `/media/*` via Django or nginx.
    Verified from code: `core/urls.py` (media serving conditions).
  - Production typically uses S3/MinIO or a CDN (see `docs/RUNBOOK.md`).

## Metadata suggestions (optional, not enforced)
Use `GiftType.metadata` to help clients render consistently:
- `type`: `static` or `animated`
- `description`: short text

Verified from code: `apps/payments/models.py: GiftType.metadata` (JSON field).

## Accessibility notes (recommended)
- Avoid flashing above 3 Hz.
- Provide sufficient contrast for overlays.
- Consider a short `description` in metadata for screen-reader hints.
