# SelfLink

click for more [`WHAT-IS-SELFLINK.md`](WHAT-IS-SELFLINK.md)

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
Full details: [`CONTRIBUTOR_REWARDS.md`](CONTRIBUTOR_REWARDS.md)

For questions or collaboration, join the Discord: https://discord.gg/GQdQagsw


## What this project is NOT
- a DAO
- a token or crypto project `But that could change because crypto is a really powerful thing, of course it's not just up to me to decide.`
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
- `make infra-up` (starts api + asgi + worker + realtime + postgres + redis + pgbouncer + media)
- `make infra-migrate`
- `make infra-superuser`
- `make infra-status` (quick health check for api/asgi ports)
- Optional search stack: `docker compose -f infra/compose.yaml --profile search up -d`
- For more, see `README_for_env.md` or `docker_guide.md`

Note: Docker Compose reads `infra/.env`; the root `.env` is only for non-Docker runs. Docker Compose interpolates `$VAR` in `infra/.env`, so escape literal `$` as `$$`. Inside containers, `localhost` does not point to other services; use Docker hostnames like `pgbouncer`, `redis`, and `opensearch`.

## Dev vs prod server modes
- `infra/compose.yaml` runs Django via `runserver` for local development.
- `infra/docker/Dockerfile.api` defaults to Gunicorn for production-like deployments.

## Realtime / SSE
- FastAPI realtime gateway (primary): `ws://localhost:8002/ws` (Docker Compose).
- ASGI dev server: `uvicorn core.asgi:application --host 0.0.0.0 --port 8001` (SSE endpoints like `/api/v1/mentor/stream/`).
- Django Channels `/ws` is deprecated; to enable legacy support set `REALTIME_CHANNELS_ENABLED=true` and use the ASGI server on port 8001.

## Realtime architecture
- FastAPI is the primary realtime gateway to keep WebSocket fanout isolated and scalable without coupling to Django request latency.
- Docker Compose starts it by default; for non-Docker runs, start `uvicorn services.realtime.app:app --host 0.0.0.0 --port 8002` and route `/ws` to that port.
- Legacy Channels clients can be migrated by switching `/ws` to the FastAPI gateway; keep `REALTIME_CHANNELS_ENABLED=true` only for temporary compatibility.

## Realtime quick test
- `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health')"` -> exit code 0

## Cloudflare Tunnel notes
- Routing for `api.self-link.com`:
  - REST + docs (`/api/v1/*`, `/api/docs/`) -> API (`http://localhost:8000`)
  - WebSockets (`/ws*`) -> FastAPI realtime gateway (`http://localhost:8002`)
  - Media (`/media/*`) -> static media server (`http://localhost:8080`)
- `cloudflared` runs on the host/systemd; use `infra/cloudflared/config.yml` and replace:
  - `tunnel: <TUNNEL_UUID>`
  - `credentials-file: /etc/cloudflared/<TUNNEL_UUID>.json`
- The media service is published only to `127.0.0.1:8080` for the host tunnel.
- `SERVE_MEDIA` is a dev fallback only; keep it `false` in production.

Cache guidance:
- Cloudflare can cache 404s; purge cache if media was missing before.
- While testing, add a Cache Rule to bypass cache for `/media/*`.
- Once stable, you can cache `/media/*` with a long TTL.
- Use `?v=timestamp` to bust cache during development.

## Media storage modes

### A) Local media (Docker + Tunnel)
- `STORAGE_BACKEND=local` (default in `infra/compose.yaml`).
- Keep the `media-data` volume and the `media` nginx service; route `/media/*` to `http://localhost:8080`.
- `SERVE_MEDIA=true` is a dev-only fallback when using Django for `/media/`.
- Verification:
  - Upload a new avatar/post image/video.
  - Confirm file exists in the API container:
    `docker compose -f infra/compose.yaml exec api ls -lah /app/media/<path>`
  - Origin check (media service): `curl -I http://localhost:8080/media/<path>`
  - Public check: `curl -I https://api.self-link.com/media/<path>?v=1`
  - Diagnostics: `python manage.py storage_status`

### B) S3/MinIO media
- `STORAGE_BACKEND=s3`
- Set `S3_ENDPOINT`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET` in `infra/.env`.
- Optional: `S3_QUERYSTRING_AUTH=true` for presigned URLs (default) or `false` for public bucket URLs.
- Start MinIO with `docker compose -f infra/compose.yaml --profile storage up -d minio` (or point to AWS S3).
- Verification:
  - Upload a new avatar/post image/video.
  - Confirm the object exists in the bucket (MinIO console or client).
  - API should return an absolute URL (starts with `http`).
  - `curl -I <absolute-media-url>`
  - Diagnostics: `python manage.py storage_status`

## BYO LLM Keys
- `/api/v1/mentor/chat/` accepts `X-LLM-Key` for user-supplied provider keys.

## License
Open source. See LICENSE.
