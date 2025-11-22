# selflink-backend

SelfLink is a social OS backend built with Django and Django REST Framework, providing auth, social graph, messaging, astro/matrix services, AI Mentor, payments, and more.

## Project Layout

```
selflink-backend/
│
├── apps/
│   ├── config/             # feature flags + runtime config cache
│   ├── core/               # shared API router, base models, pagination
│   ├── feed/               # timelines, ranking, fan-out tasks
│   ├── matrix/             # astrology + numerology data sources
│   ├── media/              # uploads, presigned URLs, media policies
│   ├── mentor/             # AI mentor sessions, prompts, memory store
│   ├── messaging/          # threads, direct messages, typing state
│   ├── moderation/         # safety rules, reports, enforcement
│   ├── notifications/      # in-app/push/email dispatch + preferences
│   ├── payments/           # plans, wallet, Stripe integrations
│   ├── reco/               # recommendation features + scoring
│   ├── search/             # OpenSearch clients, indexing tasks
│   ├── social/             # posts, comments, reactions, gifting
│   └── users/              # auth, profiles, privacy controls
│
├── services/
│   ├── realtime/           # FastAPI WebSocket gateway w/ Redis pub-sub
│   └── reco/               # worker processes for advanced ranking
│
├── core/                   # Django project: settings, ASGI/WSGI, Celery
│   ├── settings/           # base.py, dev.py, prod.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
│
├── config/                 # fixtures + seed data consumed by manage.py
│   └── fixtures/
│
├── infra/                  # Docker/K8s definitions + dev Make targets
│   ├── docker/
│   ├── compose.yaml
│   ├── k8s/
│   └── Makefile
│
├── libs/                   # shared helpers (ID generator, LLM adapters)
│   ├── idgen.py
│   ├── llm/
│   └── utils/
│
├── tests/                  # API + service regression suites
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Overview

- Users: registration, auth (email + social), profiles, privacy controls.
- Social: posts, comments, reactions, gifting, timelines/feed, recommendations.
- Messaging & realtime: threads, DMs, typing indicators, WebSocket gateway.
- Astro & matrix: natal charts, transits, matrix data, matching (SoulMatch).
- AI Mentor: LLM-powered personal guide with chat/history endpoints.
- Payments & monetization: Stripe checkout, plans, wallets.
- Moderation & safety: reports, enforcement, rate limits, banned words.
- Search & discovery: OpenSearch-backed indexing and queries.
- Notifications: in-app/push/email delivery with preferences.

## Tech Stack & Architecture

- Python, Django, Django REST Framework.
- PostgreSQL (via `DATABASE_URL`), SQLite fallback for local quickstart.
- Redis for Celery broker + pub/sub.
- Celery workers/beat for async tasks.
- OpenSearch (optional, feature-flagged).
- Docker + docker-compose (`infra/compose.yaml`) for reproducible dev stack.
- Key apps: users, social, messaging, mentor, astro, matrix, media, payments, notifications, moderation, reco, search, profile, config, core.

## Requirements & Prerequisites

- Python 3.x (match project runtime).
- pip + virtualenv.
- PostgreSQL & Redis if running services locally without Docker.
- Docker and docker-compose for containerized workflow.

## Getting Started

### Local setup

1. Create a virtualenv and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and adjust secrets.

3. Run migrations and start the server:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py runserver
   ```

4. Celery worker & beat (optional for dev):

   ```bash
   celery -A core worker -l info
   celery -A core beat -l info
   ```

## Docker Compose (Dev Stack)

The infra bundle under `infra/` provisions Postgres, Redis, OpenSearch, MinIO, Django API, Celery workers, and the realtime gateway.

```bash
make -C infra up       # build & start services
make -C infra logs     # follow logs
make -C infra down     # stop stack
make -C infra migrate  # run python manage.py migrate inside the api container
```

Manual equivalent with `docker-compose` (run from repo root):

```bash
sudo docker-compose -f infra/compose.yaml down
sudo docker-compose -f infra/compose.yaml up -d --build
sudo docker-compose -f infra/compose.yaml logs -f api
sudo docker-compose -f infra/compose.yaml exec api python manage.py migrate
```

After the stack is running the API is available on `http://localhost:8000`, realtime gateway on `ws://localhost:8001/ws`, Postgres on `localhost:5432`, Redis on `localhost:6379`, OpenSearch on `localhost:9200`, and MinIO console on `http://localhost:9001`.

### Environment configuration (.env)

Common variables (set in `.env` or host env):

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL` (e.g., `postgres://user:pass@localhost:5432/selflink`)
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (usually Redis)
- `OPENSEARCH_ENABLED`, `OPENSEARCH_HOST`, `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`
- `FEATURE_FLAGS` (e.g., `mentor_llm`, `soulmatch`, `payments`)
- `SWISSEPH_DATA_PATH` for astro data
- Mentor LLM: `MENTOR_LLM_BASE_URL`, `MENTOR_LLM_MODEL`

Example snippet:

```env
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=changeme
DATABASE_URL=postgres://selflink:selflink@localhost:5432/selflink
CELERY_BROKER_URL=redis://localhost:6379/0
OPENSEARCH_ENABLED=false
MENTOR_LLM_BASE_URL=http://localhost:11434
MENTOR_LLM_MODEL=llama3
```

## Database & Migrations

- Create new migrations: `python manage.py makemigrations` or `python manage.py makemigrations <app>`
- Apply migrations: `python manage.py migrate`
- Docker users: run the commands inside the `api` container (`docker compose -f infra/compose.yaml exec api python manage.py migrate`).
- Default DB is SQLite if `DATABASE_URL` is not set; prefer Postgres for real environments.

## API Overview

- Base path: `/api/v1/`
- OpenAPI schema: `/api/schema/`
- Docs: `/api/docs/`
- Routers (via `apps/core/api_router.py`): auth/users, social, messaging, mentor, astro, matrix, media, payments, notifications, moderation, feed, reco, profile, search.
- Auth: JWT via dj-rest-auth/SimpleJWT; typical login/register flows under `/api/v1/auth/` (see users app).

## AI Mentor Feature

- Endpoints: `POST /api/v1/mentor/chat/`, `GET /api/v1/mentor/history/` (auth required).
- Behavior: returns a placeholder reply if no LLM is configured; persists `MentorSession` and `MentorMessage`.
- LLM configuration:
  - `MENTOR_LLM_BASE_URL` (OpenAI-compatible `/v1/chat/completions`)
  - `MENTOR_LLM_MODEL` (e.g., `llama3`, `Qwen/Qwen2.5-14B-Instruct`)
- Persona prompts are loaded from text files in `apps/mentor/persona/` (e.g., `base_en.txt`, `base_ka.txt`, `base_ru.txt`) so you can tweak prompts without code changes.
- Admin visibility: `apps/mentor/admin.py` registers MentorSession/MentorMessage for inspection.

## Running the backend (dev)

- Local: `python manage.py runserver` (after env + migrate).
- Docker: `docker compose -f infra/compose.yaml up -d` then exec into `api` for commands.
- Celery: `celery -A core worker -l info` and `celery -A core beat -l info` (or via compose).

### Search Service

- OpenSearch connection is managed by `apps.search.client`. Set `OPENSEARCH_ENABLED=false` to fall back to relational lookups.
- Indexing is triggered via Celery tasks (`apps/search/tasks.py`) fired from model signals. Run a worker/beat (`celery -A core worker -l info`) to keep indices fresh.

### Recommendation Worker

- Lightweight scoring logic lives in `services/reco/engine.py`. Celery task `rebuild_user_timeline_task` rebuilds materialized feeds.
- Follow/unfollow actions enqueue rebuilds; schedule periodic refreshes via Celery beat if needed.

### Tests

- Sample API tests reside in `tests/test_api.py`. Run with `python manage.py test` after generating migrations (`python manage.py makemigrations`).
- Feature flag tests in `tests/test_feature_flags.py` exercise the new flag service.

### Demo Data

- Seed the database with demo users, posts, and baseline plans via `python manage.py seed_demo`.
- Use `python manage.py seed_demo --reset` to purge existing demo users before reseeding.

### Admin & Fixtures

- `python manage.py bootstrap_admin` provisions a superuser (configurable via `--email/--password`) and sets up moderation/support groups along with baseline feature flags.
- `python manage.py load_fixtures` loads JSON fixtures from `config/fixtures/` (override with `--path`).
- `python manage.py refresh_soulmatch_profiles` recomputes compatibility profiles (use `--user <id>` for a single user).

### AI Mentor Configuration

- Environment vars:
  - `MENTOR_LLM_ENABLED` (`true|false`) toggles use of the pluggable LLM client.
  - `MENTOR_LLM_PROVIDER` (`openai|ollama|mock`) selects the provider; `mock` returns canned replies for local dev.
  - `MENTOR_LLM_MODEL`, `OPENAI_API_KEY` configure the OpenAI client. `OLLAMA_HOST` points to a local Ollama service (defaults to `http://localhost:11434`).
  - `MENTOR_LLM_TIMEOUT` controls request timeout (seconds).
- Mentor sessions persist per-user memory (`apps.mentor.models.MentorMemory`) to inform future responses.
- To run a local model with [Ollama](https://ollama.com/): install Ollama, run `ollama serve`, pull a model (e.g., `ollama pull llama3`), then set `MENTOR_LLM_PROVIDER=ollama` and restart the backend.

### Realtime Messaging

- WebSocket gateway (`services/realtime`) now fans out events via Redis pub/sub. Configure `REALTIME_REDIS_URL` (defaults to `redis://localhost:6379/1`).
- Django publishes message events to per-user channels (`user:<id>`); multiple gateway instances stay in sync through Redis.
- If Redis is unavailable, the system falls back to in-process broadcasting and logs warnings.
- Messaging events also create in-app notifications (`apps/notifications/services.py`). Push/email delivery is stubbed and can be wired to real providers later.
- Typing indicators: `POST /api/v1/threads/<id>/typing/` toggles state; `GET` returns active typing user IDs. Events broadcast to other participants over WebSocket channels.

### Recommendation & SoulMatch

- Feature flag `FEATURE_SOULMATCH` (default true) controls availability. Override via environment variable `FEATURE_SOULMATCH=false`.
- `python manage.py refresh_soulmatch_profiles` recomputes compatibility profiles (use `--user <id>` for a single user).
- `python manage.py rebuild_soulmatch_scores` computes pairwise scores. API lives at `/api/v1/soulmatch/` (list) and `/api/v1/soulmatch/refresh/` (manual refresh).

### Payments

- Feature flag `FEATURE_PAYMENTS` (default true) controls availability.
- Configure `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, `PAYMENTS_CHECKOUT_SUCCESS_URL`, and `PAYMENTS_CHECKOUT_CANCEL_URL` in your environment.
- Set `Plan.external_price_id` to the Stripe price ID. `POST /api/v1/payments/subscriptions/` returns a `checkout_url` and `session_id` for Stripe Checkout.
- Receive Stripe webhooks at `/api/v1/payments/stripe/webhook/` to update subscription status.

### Safety & Rate Limiting

- API throttles default to `THROTTLE_USER_RATE=120/min` and `THROTTLE_ANON_RATE=60/min` (override via env vars).
- Write-heavy endpoints (posts, comments, messages, mentor asks) have additional per-user limits enforced via `django-ratelimit`.
- Users can control notification delivery (push/email/digest) and quiet hours via `PATCH /api/v1/users/me/` settings payload (`push_enabled`, `email_enabled`, `digest_enabled`, `quiet_hours`).
- Moderation APIs: regular users file reports via `/api/v1/moderation/reports/`. Staff (group `moderation_team` or admin) manage reports at `/api/v1/moderation/admin/reports/` and enforce actions via `/api/v1/moderation/enforcements/`.
- Auto-flagging: configure `MODERATION_BANNED_WORDS` (comma separated) to auto-create moderation reports for posts/messages containing banned terms.

### Observability

- Prometheus metrics exposed at `/metrics` via `django-prometheus`; run a Prometheus instance or forward metrics from that endpoint.
- Structured JSON logging enabled by default (env `APP_LOG_LEVEL` to adjust app logger verbosity).

## Tests & Quality

- Pytest (preferred): `pytest`
- Django test runner: `python manage.py test`
- Mentor API coverage: `apps/mentor/tests/test_api.py`
- Add tests for new features before opening a PR.

## Contributing

1. Fork the repo.
2. Create a feature branch: `git checkout -b feature/my-change`
3. Make focused changes and add tests.
4. Run tests locally (`pytest` or `python manage.py test`).
5. Open a Pull Request with a clear description and impact.

Guidelines:
- Follow existing Django/DRF patterns and app boundaries.
- Keep secrets/API keys out of code; rely on environment variables.
- For mentor work, keep prompts/configs in `apps/mentor/persona/` or services instead of hardcoding.
- Small, scoped PRs are easier to review.

## Documentation Index

- `backand.md` — End-to-end product blueprint dated 2025-10-29 covering vision, differentiators, architecture, and data models.
- `contrinutors.md` — Contribution guide with project values, workflow expectations, upgrade checklists, and coding/testing standards.
- `README_for_env.md` — How-to for `.env` management plus line-by-line explanations of every environment variable the stack consumes.

## License

License: TBD
