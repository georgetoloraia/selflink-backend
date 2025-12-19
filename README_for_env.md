## Overview

- `.env.example` (.env.example) is a template that lists every environment variable the backend expects so new developers can copy it to `.env` and fill in secrets without accidentally committing them.

- Environment variables keep secrets/config (keys, URLs, feature toggles) out of source control, let each environment (local, staging, prod) inject its own values, and are loaded by Django’s settings before the app starts.

## How To Use

- Copy the file: cp .env.example .env, then replace placeholder values with real credentials for your setup.
- The project’s settings module (likely via `environ/dotenv`) reads .env at startup, so updating the file immediately affects your local instance; restart services if needed.

## Variables

- `DJANGO_SECRET_KEY`: cryptographic signing key; must be long and unique in production.
- `DJANGO_DEBUG`: enables Django debug mode for local dev; set `false` in prod.
- `DJANGO_ALLOWED_HOSTS`: comma list of domains/IPs Django will serve; extend for deployed hosts.
- `DATABASE_URL`: Postgres connection string; prefer pointing to pgbouncer in Docker.
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_URL`, `PUBSUB_REDIS_URL`: Redis endpoints for Celery, caching, and realtime fanout.
- `CORS_ALLOWED_ORIGINS`: front-end origins permitted to call the API.
- `JWT_SIGNING_KEY`, `REALTIME_JWT_SECRET`: secrets for issuing/verifying tokens; **use the same value for both**.
- `OPENSEARCH_ENABLED`, `OPENSEARCH_HOST`, `OPENSEARCH_PORT`, `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`: optional OpenSearch integration.
- `OPENSEARCH_INITIAL_ADMIN_PASSWORD`: OpenSearch bootstrap password for local dev.
- `SWISSEPH_DATA_PATH`: Swiss Ephemeris data directory (e.g. `/app/astro_data`).
- `ASTRO_RULES_VERSION`, `MATCH_RULES_VERSION`: computation versioning for deterministic cache keys.
- `RECO_DEFAULT_LIMIT`, `RECO_MAX_FOLLOWS`: tuning knobs for recommendation logic.
- `MENTOR_LLM_ENABLED`, `MENTOR_LLM_PROVIDER`, `MENTOR_LLM_MODEL`, `MENTOR_LLM_TIMEOUT`: mentor AI configuration.
- `OPENAI_API_KEY`: required for OpenAI-backed mentor provider.
- `OLLAMA_HOST`: URL for a local Ollama server when mocking or running open models.
- `RATE_LIMITS_ENABLED`, `MENTOR_RPS_USER`, `MENTOR_RPS_GLOBAL`, `AUTH_RPS_IP`: Redis rate limits for mentor/auth endpoints.
- `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`: Stripe credentials for payment processing/refunds.
- `PAYMENTS_CHECKOUT_SUCCESS_URL`, `PAYMENTS_CHECKOUT_CANCEL_URL`: frontend URLs for checkout redirects.
- `THROTTLE_USER_RATE`, `THROTTLE_ANON_RATE`: DRF throttling defaults.
- `MODERATION_BANNED_WORDS`: comma list of blocked terms for moderation filters.
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `S3_ENDPOINT`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`: MinIO/S3 storage configuration.


## Natural next steps:

1. Copy `.env.example` to `.env` and supply real secrets/URLs.
2. Review Django settings to confirm how these variables are consumed and ensure unused integrations (OpenSearch, Mentor LLM, Stripe) are disabled or fully configured.
3. Create an `astro_data/` directory (or set `SWISSEPH_DATA_PATH`) and drop Swiss Ephemeris data files there before running astrology calculations.
