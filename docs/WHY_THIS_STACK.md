# Why This Stack (and how production runs)

This doc explains why each major component exists in SelfLink backend, what it solves, and how the production stack is wired. All claims are grounded in repo files (paths are cited inline).

## What the backend is (in plain terms)
SelfLink backend is the system of record for users, social graph, messaging, mentor/astro experiences, contributor rewards, and SLC credits. It exposes REST endpoints under `/api/v1/`, streams mentor responses via SSE, and serves realtime WebSocket updates through a dedicated gateway.

## Why this architecture exists
We split the stack so long‑lived connections and heavy work never block normal API requests: Django/DRF handles CRUD/auth, ASGI handles SSE, FastAPI handles WebSockets, and Celery handles slow/variable tasks. Postgres (with PgBouncer) stays the source of truth, while Redis supports caching, broker, and realtime pub/sub.

## Roadmap / Where to contribute
- **Core social features**: profiles, posts, follows, moderation.
- **Mentor + SSE + LLM**: streaming mentor endpoints, prompt safety, async jobs.
- **SLC + payments**: off‑chain ledger, payment webhooks, transfer/spend flows.
- **Contributor rewards**: append‑only ledger + monthly snapshots.
- **Infra**: routing, Docker/host mode, health checks, Cloudflared.

## Entry points (key files)
- `core/urls.py` — top‑level routing under `/api/v1/`
- `core/asgi.py` — ASGI entrypoint for SSE
- `core/celery.py` — Celery worker/beat config
- `services/realtime/app.py` — FastAPI WebSocket gateway + `/health`
- `apps/mentor/api_stream.py` — SSE mentor stream
- `apps/coin/` — SLC models/services/views
- `apps/payments/webhook.py` — Stripe webhook verification + mint
- `apps/contrib_rewards/` — rewards ledger and snapshots
- `infra/compose.yaml` — local stack definition
- `infra/cloudflared/config.yml` — host routing rules

## Quick orientation (local vs host)

- Local contributors run `make infra-up-local` which uses `infra/compose.yaml` (Makefile).
- Host mode runs `make infra-up-host` which overlays `infra/compose.host.yaml` for localhost-only bindings and gunicorn (Makefile, `infra/compose.host.yaml`).

## Why each component exists

### Django + DRF (HTTP API)
What it does:
- Primary REST API and admin UI (`core/urls.py`, `core/settings/base.py`).
- API surface is wired under `/api/v1/` (`core/urls.py`).

Why it fits here:
- Django provides the ORM and admin for a large relational domain; DRF gives standard auth/serialization/throttling (`core/settings/base.py` REST_FRAMEWORK).

If missing or misconfigured:
- `/api/v1/*` fails or returns auth/permission errors; DRF throttling and schema generation won’t work (REST_FRAMEWORK settings in `core/settings/base.py`).

### ASGI (SSE and async endpoints)
What it does:
- Runs Django’s ASGI app for SSE and async-capable endpoints (`core/asgi.py`).
- SSE mentor stream uses ASGI endpoint `/api/v1/mentor/stream/` (`apps/mentor/api_stream.py` + `apps/mentor/urls.py`).

Why it fits here:
- SSE needs an async server; separating ASGI avoids mixing streaming with WSGI request lifecycles.

If missing or misconfigured:
- SSE endpoints return errors or hang; `/api/v1/mentor/stream/` won’t stream tokens (`apps/mentor/api_stream.py`).

### FastAPI Realtime Gateway (WebSockets)
What it does:
- Dedicated WebSocket gateway at `/ws` and health endpoint `/health` (`services/realtime/app.py`).
- Uses Redis pub/sub for fanout (`services/realtime/redis_client.py`), configured via `REALTIME_REDIS_URL` (`services/realtime/config.py`).

Why it fits here:
- WebSockets are isolated from Django request latency and can scale independently.
- Keeps realtime connections out of the main Django workers.

If missing or misconfigured:
- `/ws` returns connection failures; events won’t broadcast (FastAPI `websocket_endpoint` in `services/realtime/app.py`).
- If Redis is wrong, cross-instance broadcast fails (`services/realtime/redis_client.py`).

Legacy note:
- Django Channels routes are gated behind `REALTIME_CHANNELS_ENABLED` (deprecated) (`core/routing.py`, `core/settings/base.py`).

### Celery Worker + Beat
What it does:
- Offloads heavy/variable work to background jobs (`core/celery.py`, `infra/compose.yaml` services `worker` and `beat`).

Why it fits here:
- Keeps HTTP handlers thin and responsive; long LLM or compute tasks do not block web workers.

If missing or misconfigured:
- Async endpoints return task IDs that never complete; scheduled jobs won’t run (`core/celery.py`).

### Postgres (source of truth)
What it does:
- Primary database for all domain data (`infra/compose.yaml` service `postgres`).

Why it fits here:
- Relational consistency is required for users, social graph, rewards, and audit data.

If missing or misconfigured:
- Django can’t start or migrations fail; all data APIs break.

### PgBouncer (DB pooler)
What it does:
- Pools Postgres connections for API + workers (`infra/compose.yaml` service `pgbouncer`, config in `infra/pgbouncer/pgbouncer.ini`).

Why it fits here:
- Prevents connection exhaustion when multiple services or workers scale.

If missing or misconfigured:
- DB connections spike and requests fail under load; connection limits are hit.

### Redis (broker, cache, realtime)
What it does:
- Celery broker + result backend (`core/settings/base.py`, `infra/compose.yaml` service `redis`).
- Django cache if `REDIS_URL` set (`core/settings/base.py`).
- Realtime pub/sub for FastAPI (`services/realtime/redis_client.py`).

Why it fits here:
- Low-latency queueing and pub/sub; standard for Celery and realtime fanout.

If missing or misconfigured:
- Tasks never execute; rate limits and caches fail; realtime fanout stops.

### Nginx media
What it does:
- Serves `/media/*` from a shared volume (`infra/compose.yaml` service `media`, config in `infra/nginx/media.conf`).

Why it fits here:
- Avoids Django serving media in production-like setups; keeps media serving simple.

If missing or misconfigured:
- Media URLs 404; clients can’t load uploads.

### Cloudflared (edge routing)
What it does:
- Routes public paths to local services with a strict first-match ordering (`infra/cloudflared/config.yml`).

Why it fits here:
- Provides TLS + public ingress without opening container ports to the world.

If missing or misconfigured:
- Requests go to the wrong backend (e.g., SSE routed to the API), or `/ws` fails.

### Optional OpenSearch (search)
What it does:
- Search/indexing stack, enabled via compose profile `search` (`infra/compose.yaml`).

Why it fits here:
- Only needed if search features require indexing beyond Postgres.

If missing or misconfigured:
- Search endpoints that depend on OpenSearch will fail (if enabled).

### Optional MinIO (S3-compatible storage)
What it does:
- Local S3-compatible object storage, enabled via compose profile `storage` (`infra/compose.yaml`).

Why it fits here:
- Mirrors S3 workflows for media/object storage without external AWS dependency.

If missing or misconfigured:
- Storage backend operations fail when `STORAGE_BACKEND=s3`.

## Design principles (repo-grounded)

- Postgres is the source of truth for domain data (`docs/architecture/domains.md`, `docs/architecture/diagram.md`).
- Heavy/variable work moves to Celery; streaming stays in ASGI/FastAPI (`docs/ARCHITECTURE.md`, `core/celery.py`, `apps/mentor/api_stream.py`, `services/realtime/app.py`).
- Domain boundaries: Core vs Intelligence separation with explicit dependency rules (`docs/architecture/domains.md`).
- Determinism/auditability: rewards are append-only with snapshots; astro is deterministic and cacheable by rules version (`docs/ARCHITECTURE.md`).

## How production runs (ports, routing, processes)

### Process model and ports
- **API (Django/DRF)**: host `8000` → container `8000` (`infra/compose.yaml` service `api`).
- **ASGI (SSE)**: host `8001` → container `8001` (`infra/compose.yaml` service `asgi`).
- **Realtime WS (FastAPI)**: host `8002` → container `8001` (`infra/compose.yaml` service `realtime`, `services/realtime/app.py`).
- **Media (nginx)**: host `8080` → container `8080` (`infra/compose.yaml` service `media`, `infra/nginx/media.conf`).
- **Workers / Beat**: no ports exposed (`infra/compose.yaml`).

Host mode binds these ports to `127.0.0.1` to avoid public exposure (`infra/compose.host.yaml`).

### Startup sequence (typical)
1. `make infra-up-host` (starts containers) (Makefile).
2. `make infra-migrate` (applies database migrations) (Makefile).
3. Start Cloudflared or a reverse proxy on the host to expose routes (`infra/cloudflared/config.yml`).

Compose uses `depends_on` for ordering but does not health‑gate startup (`infra/compose.yaml`).

### Health checks
Use `make infra-status` which probes:
- `http://127.0.0.1:8000/api/docs/`
- `http://127.0.0.1:8001/api/docs/`
- `http://127.0.0.1:8002/health`
(`Makefile`)
Optional SLC invariant check (read-only): `make coin-invariant-check` (`Makefile`).

### Required env groups (host mode)
From `infra/.env.example` and `core/settings/base.py`:
- **Core**: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG=false`
- **DB**: `DATABASE_URL` (Docker hostname like `pgbouncer`)
- **Redis/Celery**: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_URL`, `PUBSUB_REDIS_URL`
- **Realtime**: `REALTIME_JWT_SECRET` (or `JWT_SIGNING_KEY` fallback), `REALTIME_REDIS_URL`

### Cloudflared routing (first match wins)
Ordering in `infra/cloudflared/config.yml`:
1. `/ws*` → `http://localhost:8002` (FastAPI WebSockets)
2. `/api/v1/mentor/stream*` → `http://localhost:8001` (ASGI SSE)
3. `/media/*` → `http://localhost:8080`
4. `/api*` → `http://localhost:8000`
5. catch‑all → `http://localhost:8000`

If `/api*` is above the SSE path, `/api/v1/mentor/stream/` will be misrouted.

## FAQ

**Why not do WebSockets only in Django Channels?**
Channels is deprecated here and gated by `REALTIME_CHANNELS_ENABLED` (`core/routing.py`). The FastAPI gateway isolates long‑lived WS connections from Django request latency and scales independently (`services/realtime/app.py`).

**Why not run everything behind one port?**
SSE, REST, and WS have different runtime needs. Separate services keep streaming and WS from blocking the main API, and allow independent scaling (`infra/compose.yaml` services `api`, `asgi`, `realtime`).

**Why PgBouncer?**
Django + Celery can create many DB connections. PgBouncer pools them to avoid hitting Postgres limits (`infra/compose.yaml`, `infra/pgbouncer/pgbouncer.ini`).

**What does Redis do here?**
Celery broker + results, Django cache (if enabled), and realtime pub/sub (`core/settings/base.py`, `services/realtime/redis_client.py`).

**When should we add OpenSearch/MinIO?**
Enable OpenSearch when search/indexing features need it (`infra/compose.yaml` profile `search`). Enable MinIO when running S3‑compatible storage locally or in a self‑hosted setup (`infra/compose.yaml` profile `storage`).
