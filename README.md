# selflink-backend

## Project Layout

```
selflink-backend/
│
├── apps/
│   ├── core/               # shared mixins, pagination, API router
│   ├── users/              # auth, profiles, privacy controls
│   ├── social/             # posts, comments, likes, follow, feed fan-out
│   ├── messaging/          # threads, direct messages, read receipts
│   ├── mentor/             # AI mentor sessions, tasks, profiles
│   ├── matrix/             # astro + numerology logic
│   ├── payments/           # plans, subscriptions, wallet, gifts
│   ├── notifications/      # in-app notifications API
│   ├── moderation/         # user-generated reports & enforcement
│   └── feed/               # feed services + Celery tasks
│
├── services/
│   ├── realtime/           # FastAPI WebSocket gateway
│   └── reco/               # recommendation workers (placeholder)
│
├── core/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   └── Dockerfile.realtime
│   ├── compose.yaml
│   ├── k8s/
│   └── Makefile
│
├── libs/                   # shared libraries (Snowflake ID generator)
├── tests/
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Getting Started

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
```

After the stack is running the API is available on `http://localhost:8000`, realtime gateway on `ws://localhost:8001/ws`, Postgres on `localhost:5432`, Redis on `localhost:6379`, OpenSearch on `localhost:9200`, and MinIO console on `http://localhost:9001`.

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
