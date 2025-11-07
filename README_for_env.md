## Overview

- `.env.example` (.env.example) is a template that lists every environment variable the backend expects so new developers can copy it to `.env` and fill in secrets without accidentally committing them.

- Environment variables keep secrets/config (keys, URLs, feature toggles) out of source control, let each environment (local, staging, prod) inject its own values, and are loaded by Django’s settings before the app starts.

## How To Use

- Copy the file: cp .env.example .env, then replace placeholder values with real credentials for your setup.
- The project’s settings module (likely via `environ/dotenv`) reads .env at startup, so updating the file immediately affects your local instance; restart services if needed.

## Variables

- `DJANGO_SECRET_KEY` (.env.example (line 1)): cryptographic signing key; must be long and unique in production.
- `DJANGO_DEBUG` (.env.example (line 2)): enables Django debug mode for local dev; set `false` in prod.
- `DJANGO_ALLOWED_HOSTS` (.env.example (line 3)): comma list of domains/IPs Django will serve; extend for deployed hosts.
- `DATABASE_URL` (.env.example (line 4)): full Postgres connection string; swap credentials/host for your DB.
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (.env.example (lines 5-6)): Redis endpoints used by Celery for task queue and result storage; point to your Redis service.
- `CORS_ALLOWED_ORIGINS` (.env.example (line 7)): front-end origins permitted to call the API; add deployed frontend URL.
- `JWT_SIGNING_KEY`, `REALTIME_JWT_SECRET` (.env.example (lines 8-9)): secrets for issuing/verifying authentication tokens; generate strong unique values.
- `OPENSEARCH_ENABLED`, `OPENSEARCH_HOST`, `OPENSEARCH_PORT`, `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD` (.env.example (lines 10-14)): configure optional OpenSearch integration; disable or supply credentials depending on whether search is deployed.
`RECO_DEFAULT_LIMIT`, `RECO_MAX_FOLLOWS` (.env.example (lines 15-16)): tuning knobs for recommendation logic; adjust to match product requirements.
- `MENTOR_LLM_ENABLED`, `MENTOR_LLM_PROVIDER`, `MENTOR_LLM_MODEL`, `MENTOR_LLM_TIMEOUT` (.env.example (lines 17-21)): toggle and configure the mentor AI integration; set provider/model plus timeout for the LLM service you use.
- `OPENAI_API_KEY` (.env.example (line 20)): required if the LLM provider needs OpenAI; leave blank if unused.
- `OLLAMA_HOST` (.env.example (line 22)): URL for a local Ollama server when mocking or running open models.
- `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` (.env.example (lines 23-24)): Stripe credentials for payment processing/refunds; must use live keys in production.
- `PAYMENTS_CHECKOUT_SUCCESS_URL`, `PAYMENTS_CHECKOUT_CANCEL_URL` (.env.example (lines 25-26)): frontend URLs Stripe redirects to after checkout; replace with your deployed frontend paths.
- `THROTTLE_USER_RATE`, `THROTTLE_ANON_RATE` (.env.example (lines 27-28)): API rate limiting values (requests per minute); tighten in production if needed.
- `MODERATION_BANNED_WORDS` (.env.example (line 29)): comma list of blocked terms for moderation filters; extend as policy evolves.


## Natural next steps:

1. Copy `.env.example` to `.env` and supply real secrets/URLs.
2. Review Django settings to confirm how these variables are consumed and ensure unused integrations (OpenSearch, Mentor LLM, Stripe) are disabled or fully configured.