# SelfLink

click for more [`WHAT-IS-SELFLINK.md`](WHAT-IS-SELFLINK.md)

This repository contains the backend.
Start here: `START_HERE.md`
The mobile app lives here: https://github.com/georgetoloraia/selflink-mobile


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

## Quickstart (backend)
- Clone the repo and copy `infra/.env.example` to `infra/.env` (keep `$$` escapes for Compose)
- `make infra-up` (starts api + asgi + worker + realtime + postgres + redis + pgbouncer + media)
- `make infra-migrate`
- `make infra-superuser`
- `make infra-status` (informational health check)
- `make infra-status-strict` (fails if api/asgi/realtime are not healthy)
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

## Mentor async defaults
- Non-stream mentor endpoints enqueue Celery tasks by default and return `202` with a `task_id`.
- Poll `/api/v1/mentor/task-status/<task_id>/` for `pending` or `ready` results.
- Force sync (debug only) with `X-Sync: true` or `?async=false`.
- SSE streaming stays synchronous via ASGI at `/api/v1/mentor/stream/`.

Examples:
```
curl -X POST http://localhost:8000/api/v1/mentor/chat/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"I feel stuck"}'

curl -X POST http://localhost:8000/api/v1/mentor/chat/ \
  -H "Authorization: Bearer <token>" \
  -H "X-Sync: true" \
  -H "Content-Type: application/json" \
  -d '{"message":"I feel stuck"}'

curl -N "http://localhost:8001/api/v1/mentor/stream/?message=hi" \
  -H "Authorization: Bearer <token>"
```

## License
Open source. See LICENSE.
