# SelfLink Backend — Production Runbook

This runbook explains how the backend runs on a server and how to operate it. All statements are grounded in repo files: `infra/compose.yaml`, Dockerfiles, Makefiles, `core/settings/base.py`, `core/celery.py`, and `services/realtime/*`.

---

## 1) Process Model (what runs and why)

**API (Django/DRF, HTTP)**
- Compose command: `python manage.py runserver 0.0.0.0:8000` (`infra/compose.yaml` service `api`).
- Production default in Dockerfile: `gunicorn core.wsgi:application --bind 0.0.0.0:8000` (`infra/docker/Dockerfile.api`).
- Routes via `core/urls.py` → `apps.core.api_router` (`core/urls.py`, `apps/core/api_router.py`).

**ASGI (SSE and ASGI endpoints)**
- Command: `uvicorn core.asgi:application --host 0.0.0.0 --port 8001` (`infra/compose.yaml` service `asgi`).
- Handles SSE endpoints like `/api/v1/mentor/stream/` (`apps/mentor/api_stream.py`).

**Realtime Gateway (FastAPI WebSockets)**
- Command: `uvicorn services.realtime.app:app --host 0.0.0.0 --port 8001` (`infra/docker/Dockerfile.realtime`).
- WebSocket endpoint `/ws` with JWT query param; Redis pub/sub fanout (`services/realtime/app.py`, `services/realtime/redis_client.py`).
- Health endpoint `/health` (`services/realtime/app.py`).

**Celery Worker**
- Command: `celery -A core worker -l info` (`infra/compose.yaml` service `worker`).
- App config: `core/celery.py` and settings in `core/settings/base.py`.

**Celery Beat**
- Command: `celery -A core beat -l info` (`infra/compose.yaml` service `beat`, profile `beat`).
- Schedule defined in `core/settings/base.py` `CELERY_BEAT_SCHEDULE`.

**Postgres**
- Service: `postgres:15-alpine` (`infra/compose.yaml`).
- Schema is the source of truth; Django connects via `DATABASE_URL` (`core/settings/base.py`).

**PgBouncer**
- Service: `edoburu/pgbouncer:1.22.1-p0` (`infra/compose.yaml`).
- Pooling config in `infra/pgbouncer/pgbouncer.ini`.

**Redis**
- Service: `redis:7-alpine` (`infra/compose.yaml`).
- Used as Celery broker/result backend and Django cache when `REDIS_URL` is set (`core/settings/base.py`).
- Used for realtime pub/sub (`services/realtime/redis_client.py`).

---

## 2) Startup Sequence (recommended order)

Compose wiring uses `depends_on` (not health‑gated) to define basic order (`infra/compose.yaml`).

**Recommended boot order:**
1. **Postgres** (db)
2. **PgBouncer** (pooler depends on Postgres)
3. **Redis** (broker/cache/pubsub)
4. **Migrations** (manual step): `docker compose -f infra/compose.yaml exec api python manage.py migrate` (`Makefile` target `infra-migrate`)
5. **API / ASGI / Realtime / Worker / Beat**

---

## 3) Required Environment Variables (grouped by service)

> Compose loads env from `infra/.env` via `env_file` (`infra/compose.yaml`).  
> Settings read via `core/settings/base.py` and `services/realtime/config.py`.

### Django API / ASGI / Worker / Beat (secrets marked)
**Core runtime**
- `DJANGO_SECRET_KEY` **(secret)** — used by Django (`core/settings/base.py` `SECRET_KEY`).
- `DJANGO_ALLOWED_HOSTS` — required in prod (`core/settings/base.py`).
- `DJANGO_DEBUG` — should be `false` in prod (`core/settings/base.py`).

**Database**
- `DATABASE_URL` **(secret if includes password)** — Django DB connection (`core/settings/base.py`).
  - Docker guardrail: `validate_database_url_for_docker` rejects `localhost` inside Docker (`core/settings/base.py`).

**JWT / Auth**
- `JWT_SIGNING_KEY` **(secret)** — signing JWTs (`core/settings/base.py` `SIMPLE_JWT`).
  - Defaults to `DJANGO_SECRET_KEY` if unset.

**Redis / Celery**
- `CELERY_BROKER_URL` — Celery broker (`core/settings/base.py`).
- `CELERY_RESULT_BACKEND` — Celery result backend (`core/settings/base.py`).
- `REDIS_URL` — Django cache uses Redis if set (`core/settings/base.py`).
- `PUBSUB_REDIS_URL` — Channels/realtime pubsub default (`core/settings/base.py`).

**Storage**
- `STORAGE_BACKEND` — `local` or `s3` (`core/settings/base.py`).
- `SERVE_MEDIA` — allow Django media serving (`core/urls.py`).
- If `STORAGE_BACKEND=s3`: `S3_ENDPOINT`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET` **(secrets)** (`core/settings/base.py`).

**Optional integrations**
- OpenSearch: `OPENSEARCH_ENABLED`, `OPENSEARCH_HOST`, `OPENSEARCH_PORT`, `OPENSEARCH_USERNAME`, `OPENSEARCH_PASSWORD` **(secret)** (`core/settings/base.py`).
- Rate limits: `RATE_LIMITS_ENABLED`, `MENTOR_RPS_USER`, `MENTOR_RPS_GLOBAL`, `AUTH_RPS_IP` (`core/settings/base.py`, `apps/core_platform/rate_limit.py`).
- Mentor LLM:
  - `MENTOR_LLM_PROVIDER`, `MENTOR_LLM_MODEL` (`libs/llm/client.py`)
  - `OPENAI_API_KEY` **(secret)** (`libs/llm/client.py`)
  - `OLLAMA_HOST` (`libs/llm/client.py`)
  - `MENTOR_LLM_BASE_URL` (`apps/mentor/services/llm_client.py`)
  - `MENTOR_LLM_TIMEOUT` (`libs/llm/client.py`, `apps/mentor/services/llm_client.py`)

**Payments (if used)**
- `STRIPE_API_KEY` **(secret)**, `STRIPE_WEBHOOK_SECRET` **(secret)** (`apps/payments/clients/stripe.py`).
- `PAYMENTS_CHECKOUT_SUCCESS_URL`, `PAYMENTS_CHECKOUT_CANCEL_URL` (`apps/payments/serializers.py`).

### Realtime Gateway (FastAPI)
- `REALTIME_JWT_SECRET` **(secret)** — preferred JWT secret (`services/realtime/config.py`).
- `JWT_SIGNING_KEY` **(secret)** — fallback JWT secret (`services/realtime/config.py`).
- `REALTIME_REDIS_URL` — Redis pub/sub for fanout (`services/realtime/config.py`).

Optional:
- `REALTIME_HOST`, `REALTIME_PORT` if using `services/realtime/main.py` (`services/realtime/config.py`).

### Postgres (container)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` **(secret)** (`infra/compose.yaml`).

### PgBouncer
- Uses `infra/pgbouncer/pgbouncer.ini` and `infra/pgbouncer/userlist.txt` (credentials stored there).

### Redis (container)
- No env required in compose (`infra/compose.yaml`).

---

## 4) Health Checks

From `infra/compose.yaml`:

- **API**: `/api/docs/`  
  `python -c "urllib.request.urlopen('http://localhost:8000/api/docs/')"`  
  (`infra/compose.yaml` service `api` healthcheck).
- **ASGI**: `/api/docs/`  
  `python -c "urllib.request.urlopen('http://localhost:8001/api/docs/')"`  
  (`infra/compose.yaml` service `asgi` healthcheck).
- **Realtime**: `/health`  
  `python -c "urllib.request.urlopen('http://localhost:8001/health')"` inside container  
  (`infra/compose.yaml`, `services/realtime/app.py`).
- **Redis**: `redis-cli ping` (`infra/compose.yaml`).
- **Postgres**: `pg_isready -U selflink -d selflink` (`infra/compose.yaml`).
- **OpenSearch** (optional): `/_cluster/health` with admin password (`infra/compose.yaml`).

Operational shortcut:
- `make infra-status` (informational) or `make infra-status-strict` (fails if unhealthy) (`Makefile`).

---

### Mentor async task status endpoint

Mentor endpoints that return `202` provide a `task_id`. Clients can poll this endpoint to retrieve results.

**Endpoint**
- `GET /api/v1/mentor/task-status/<task_id>/` (requires auth; uses `apps/mentor/api_views/views.py` `MentorTaskStatusView`).

**Response shapes**

Ready:
```
{
  "task_id": "task-123",
  "status": "ready",
  "message": {
    "id": 45,
    "session_id": 12,
    "role": "assistant",
    "content": "...",
    "meta": {"task_id": "task-123", "task_version": "v1"},
    "created_at": "2024-01-01T12:00:00Z"
  },
  "session": {
    "id": 12,
    "mode": "natal_mentor",
    "date": "2024-01-01",
    "metadata": {"natal_chart_id": 9}
  }
}
```

Pending:
```
{ "task_id": "task-123", "status": "pending" }
```

Not found (404):
```
{ "detail": "Task not found." }
```

---

## 5) Scaling

**API / ASGI**
- Stateless code; scale horizontally if DB/Redis can handle it.
- Use shared storage (S3/MinIO) if scaling across hosts; local volume `media-data` is not shared (`infra/compose.yaml`, `core/settings/base.py`).

**Realtime**
- Each instance holds in‑memory WebSocket connections (`services/realtime/manager.py`), so you need **sticky sessions** for WS routing.
- Redis pub/sub enables cross‑instance broadcast (`services/realtime/redis_client.py`).

**Celery Worker**
- Scale workers horizontally; all use the same broker (`CELERY_BROKER_URL` in `core/settings/base.py`).

**PgBouncer sizing**
- Current defaults: `max_client_conn = 200`, `default_pool_size = 20`, `pool_mode = transaction` (`infra/pgbouncer/pgbouncer.ini`).
- Increase pool sizes with API/worker scale.

**Redis bottlenecks**
- Redis is used for Celery broker/results, cache, and pub/sub (`core/settings/base.py`, `services/realtime/redis_client.py`).
- Consider separate Redis instances/DBs if broker latency or pub/sub drops become an issue.

---

## 6) Failure Modes & Symptoms

**DB connection exhaustion**
- Symptoms: connection refused / pool errors from Django.
- Likely cause: PgBouncer `max_client_conn` too low or bypassed (`infra/pgbouncer/pgbouncer.ini`, `core/settings/base.py` `DATABASE_URL`).

**Slow LLM calls blocking web workers**
- Sync LLM calls happen in request thread in:
  - `apps/mentor/api_views/views.py` `MentorChatView.post` (uses `llm_client.chat`)
  - `apps/mentor/views.py` `NatalMentorView`, `DailyMentorView`, `SoulmatchMentorView` (uses `generate_llama_response`)
  - SSE streaming uses direct streaming calls (`apps/mentor/api_stream.py`, `apps/mentor/services/llm_client.py`)
- Symptoms: high request latency, worker timeouts.

**Redis eviction / pubsub issues**
- Symptoms: missed realtime events, Celery tasks not enqueued, rate limits bypassed.
- Evidence of dependency: `CELERY_BROKER_URL`, `REDIS_URL`, `PUBSUB_REDIS_URL` (`core/settings/base.py`), `services/realtime/redis_client.py`.

---

## 7) Observability

**Logging**
- Request bodies are stripped by `StripRequestBodyFilter` (`apps/core/logging_filters.py`).
- Logging config uses JSON formatter by default (`core/settings/base.py` `LOGGING`).

**Metrics**
- Prometheus middleware enabled: `django_prometheus.middleware.PrometheusBeforeMiddleware` / `AfterMiddleware` (`core/settings/base.py`).

---

## 8) Minimal Production Checklist (Go‑Live)

1. Set secrets:
   - `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, `REALTIME_JWT_SECRET` (`core/settings/base.py`, `services/realtime/config.py`).
2. Set `DATABASE_URL` to Postgres via PgBouncer (not `localhost` in Docker) (`core/settings/base.py` guardrail).
3. Configure Redis URLs (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_URL`, `PUBSUB_REDIS_URL`) (`core/settings/base.py`).
4. Run migrations: `docker compose -f infra/compose.yaml exec api python manage.py migrate` (`Makefile`).
5. Use production server for API (Gunicorn as per `infra/docker/Dockerfile.api`).
6. Confirm health checks:
   - `/api/docs/` (API + ASGI), `/health` (realtime), Redis ping, `pg_isready` (`infra/compose.yaml`).
7. Choose storage:
   - `STORAGE_BACKEND=s3` with S3 envs for multi‑host scaling, or ensure shared volume (`core/settings/base.py`).
8. Enable rate limits for prod if desired: `RATE_LIMITS_ENABLED=true` (`apps/core_platform/rate_limit.py`).

---

## Appendix: Key Runtime Files
- `infra/compose.yaml`
- `infra/docker/Dockerfile.api`
- `infra/docker/Dockerfile.realtime`
- `core/settings/base.py`
- `core/celery.py`
- `services/realtime/app.py`
- `services/realtime/config.py`
- `infra/pgbouncer/pgbouncer.ini`
