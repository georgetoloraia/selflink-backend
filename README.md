# SelfLink

SelfLink is an open-source backend + mobile app experimenting with a simple idea:  
Can we build software where contributors are rewarded transparently, enforced by code instead of promises?

This repository contains the backend.  
Start here: `START_HERE.md`  
The mobile app lives here: https://github.com/georgetoloraia/selflink-mobile

## What exists today
- Django / DRF backend running on a real domain
- React Native / Expo mobile app connected to it
- Auth and core flows working end-to-end
- Append-only contributor rewards ledger
- Deterministic monthly reward calculation (no manual edits)  
This is an early-stage project, but it is already real and working.

## One-sentence mental model
Every merged contribution becomes an immutable event; events are aggregated monthly; rewards are calculated mechanically. Everything else is an implementation detail.

## Why this project exists
Most platforms rely on trust, discretion, or closed accounting when it comes to value distribution. SelfLink tries a different approach:
- no retroactive edits
- no hidden rules
- no subjective reward decisions
If something is rewarded, it is:
- recorded
- auditable
- reproducible

## Architecture (high level)
```
Mobile App (Expo)
        |
        v
Django API (DRF)
        |
        v
RewardEvent Ledger (append-only)
        |
        v
Monthly Snapshot → Payouts
```

## How to contribute
There are three simple ways to help:
1) Backend (Django / DRF): See CONTRIBUTING.md
2) Mobile (React Native / Expo): https://github.com/georgetoloraia/selflink-mobile
3) Architecture / design feedback: Open an issue — no code required  
If you’re new, start with a good first issue.

## Contributor rewards (short version)
- 50% of future net platform revenue is reserved for contributors
- Contributions are tracked as immutable RewardEvents
- Rewards are calculated monthly using deterministic rules
- Corrections happen via new events, never by rewriting history  
Full details: CONTRIBUTOR_REWARDS.md


## What this project is NOT
- a DAO
- a token or crypto project
- a finished product
- a promise of guaranteed income  
It is an experiment in trust, transparency, and simplicity.

## Status
- Actively developed
- Open to contributors
- Early feedback is especially valuable  
If something feels unclear or over-engineered, that’s a bug — please point it out.

## Quickstart (backend)
- Clone the repo and copy `infra/.env.example` to `infra/.env` (keep `$$` escapes for Compose)
- `make infra-up` (starts api + asgi + worker + postgres + redis + pgbouncer)
- `make infra-migrate`
- `make infra-superuser`
- `make infra-status` (quick health check for api/asgi ports)
- Optional search stack: `docker compose -f infra/compose.yaml --profile search up -d`
- For more, see `README_for_env.md` or `docker_guide.md`

Note: Docker Compose interpolates `$VAR` in `infra/.env`; escape literal `$` as `$$` to avoid warnings.

## Realtime / SSE
- ASGI dev server: `uvicorn core.asgi:application --host 0.0.0.0 --port 8001`
- Mentor SSE endpoint: `/api/v1/mentor/stream/` (served from ASGI)

## Cloudflare Tunnel notes
- Route `/ws` to the ASGI service (port 8001) and all other paths to the API service (port 8000).
- Add `api.self-link.com` to `DJANGO_ALLOWED_HOSTS` in `infra/.env`.
- Set `SERVE_MEDIA=true` to serve `/media/` directly from Django behind the tunnel.
- Example `cloudflared` ingress:
```
ingress:
  - hostname: api.self-link.com
    path: /ws*
    service: http://localhost:8001
  - hostname: api.self-link.com
    service: http://localhost:8000
  - service: http_status:404
```
- If Cloudflare cached old 404s for media, purge cache or use a cache-busting query param.
- Quick check: `curl -I https://api.self-link.com/media/avatars/<uuid>.jpeg?v=1`

## Media check (Docker + Tunnel)
- Ensure `SERVE_MEDIA=true` in `infra/.env` and restart containers.
- Docs check: `curl -I http://localhost:8000/api/docs/`
- Origin test: `curl -I http://localhost:8000/media/avatars/<uuid>.jpeg`
- ASGI test: `curl -I http://localhost:8001/media/avatars/<uuid>.jpeg`
- Tunnel test: `curl -I https://api.self-link.com/media/avatars/<uuid>.jpeg?v=1`
- Local verify: `python manage.py check_media --path "avatars/<uuid>.jpeg"`
- Cloudflare may cache 404s; purge cache or bypass cache for `/media/*`.

## BYO LLM Keys
- `/api/v1/mentor/chat/` accepts `X-LLM-Key` for user-supplied provider keys.

## License
Open source. See LICENSE.
