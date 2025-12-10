# Contributing to selflink-backend

Thanks for your interest in strengthening **selflink-backend**. This document collects everything you need to get productive fast, upgrade safely, and ship resilient code. Start here whenever you plan to touch the codebase or roll out new releases.

## Project Values

- **Safety first**: protect user data, privacy, and platform integrity.
- **Incremental delivery**: ship small, reviewable changes with tests.
- **Observable systems**: logs, metrics, and alerts are part of every feature.
- **Inclusive collaboration**: document decisions, explain trade-offs, and be respectful in reviews.

## Local Environment Checklist

1. Clone the repository and create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env`, then set API keys, database credentials, and feature flags as needed.
3. Apply migrations and boot the stack:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py runserver
   ```
4. Optional services:
   - Start Celery workers for background tasks:
     ```bash
     celery -A core worker -l info
     celery -A core beat -l info
     ```
   - Use `make -C infra up` to run the full Docker Compose dev stack (Postgres, Redis, OpenSearch, MinIO, realtime gateway).
5. Verify the API at `http://localhost:8000` and websocket gateway at `ws://localhost:8001/ws`.

### 15-Minute Quickstart

- `make install` (or `pip install -r requirements.txt`)
- Copy `.env.example` to `.env` and set `DATABASE_URL`, `CELERY_BROKER_URL`, and `REDIS_URL`.
- `make migrate && make runserver` for a local-only stack, or `make compose-up` for the full Docker Compose stack.
- Run a dry-run reward payout to see the ledger flow: `make rewards-dry-run PERIOD=$(date +%Y-%m) REVENUE=100000 COSTS=20000`.

## Upgrade Guide

Follow this checklist whenever you pull a new release, upgrade dependencies, or prepare a production rollout.

### 1. Read the Change Log

- Check release notes, `roadmap.txt`, and recent PR descriptions.
- Look for breaking changes in settings, migrations, Celery tasks, or external services.

### 2. Refresh Dependencies

- Upgrade pinned packages carefully:
  ```bash
  pip install -r requirements.txt
  ```
- For Dockerized environments, rebuild services:
  ```bash
  make -C infra build
  make -C infra up
  ```
- If a dependency bump requires code changes, isolate them in a dedicated branch and describe test coverage in the PR.

### 3. Apply Database Changes

- Run migrations locally before touching production:
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- Review generated SQL (`python manage.py sqlmigrate app_name migration_name`) for potentially dangerous operations.
- For production upgrades:
  1. Put the site into maintenance if downtime is unavoidable.
  2. Backup the production database.
  3. Run `python manage.py migrate`.
  4. Restore services and verify key flows.

### 4. Validate the Stack

- Run the automated test suite:
  ```bash
  python manage.py test
  ```
- Exercise critical flows manually (auth, mentor sessions, feed, payments).
- Check logs (`python manage.py tail_logs` if configured, or `docker compose logs`) for regressions.
- Watch metrics exposed at `/metrics` when available.

### 5. Post-Upgrade Tasks

- Regenerate demo data or caches if necessary:
  ```bash
  python manage.py seed_demo --reset
  python manage.py rebuild_soulmatch_scores
  ```
- Restart Celery workers and the realtime gateway to pick up new code.
- Communicate upgrade status in the project channel and open follow-up issues for remaining work.

## Contribution Workflow

1. **Pick or propose work**
   - Browse issues, `tasks.txt`, and `roadmap.txt`.
   - Comment on the issue you plan to tackle; outline your approach before coding.
2. **Create a focused branch**
   - Suggested pattern: `feature/<short-description>`, `bugfix/<ticket-id>`, or `chore/<scope>`.
3. **Develop iteratively**
   - Keep commits small, narrative, and logically grouped.
   - Align with project values; note design trade-offs in commit messages or PR description.
4. **Keep your branch current**
   - Rebase on `main` regularly to avoid long-lived divergence.
5. **Open a Pull Request**
   - Fill in the PR template (if present) and list:
     - Problem statement
     - Solution summary
     - Testing performed (`python manage.py test`, manual flows)
     - Follow-up tasks or known gaps
   - Request review from maintainers listed in `backand.md` (if available) or tag `@selflink-backend/core`.

## Coding Standards

- **Python style**: follow PEP 8 and use type hints where possible.
- **Django patterns**: favor class-based views, DRF serializers, and service objects in `apps/<domain>/services.py`.
- **Settings**: use `core/settings/base.py` & `core/settings/dev.py` for configuration; never hard-code secrets.
- **Logging**: use `structlog` or the configured logging utilities; prefer structured JSON logs.
- **Celery tasks**: declare idempotent tasks and document expected retries/backoffs.
- **Observability**: expose metrics and health signals for long-running services.
- **Docs & comments**: update relevant markdown, docstrings, and inline comments when behavior changes.

## Testing Expectations

- Unit tests live under `tests/` or alongside the app module (`apps/<domain>/tests`).
- Always add regression tests when fixing bugs.
- For API changes, cover both success and failure paths (HTTP status codes, validation errors).
- When adding Celery tasks or signals, test idempotency and race conditions.
- Run the full suite before requesting review:
  ```bash
  python manage.py test
  ```
- If additional services are required (e.g., OpenSearch), ensure they are running or use feature flags (`OPENSEARCH_ENABLED=false`) to isolate tests.

## Adding New Features

1. Draft a short technical design if the change is non-trivial (use `docs/` or linkable gist).
2. Confirm feature toggles or migrations are planned.
3. Introduce API changes versioned under `apps/core/api_router.py`.
4. Update serializers, permissions, and pagination as needed.
5. Document API endpoints via OpenAPI schema or markdown tables (see README conventions).
6. Provide seed data if the feature depends on specific fixtures.
7. Validate that Celery tasks, signals, or background jobs are reboot-safe.

## Fixing Bugs

1. Reproduce the issue locally or with a failing test.
2. Capture logs, stack traces, and affected endpoints.
3. Add a regression test that fails before the fix.
4. Implement the minimal fix; avoid drive-by refactors.
5. Verify dependent flows (auth, notifications, payments) if the bug might touch shared code.
6. Update documentation or `.env.example` if configuration has changed.

## Strengthening the Codebase

- Pay down tech debt by extracting shared logic into `libs/`.
- Add metrics and alerts for fragile areas (payments, mentor responses, moderation).
- Improve database performance: analyze queries with `django-debug-toolbar` or EXPLAIN plans before indexing.
- Expand typing coverage and adopt dataclasses or pydantic models where appropriate.
- Write smoke tests for critical workflows (signup, posting, subscriptions, mentor sessions).
- Keep `roadmap.txt` updated with research spikes, experiments, and pending migrations.

## Documentation & Communication

- Update `README.md` when setup steps, environment variables, or deployment topology changes.
- Add detailed notes to `backand.md` if backend architecture evolves.
- Record design decisions in `docs/architecture/` (create this directory if it does not exist) for future contributors.
- Share progress in the project chat or issue tracker; async updates keep the team aligned across time zones.

## Security & Responsible Disclosure

- Do not open public issues for critical security vulnerabilities. Email maintainers (see `LICENSE` or project website) with full details.
- Rotate secrets that may have leaked; add mitigation steps to the PR description.
- Harden endpoints with permissions, throttles, and validation. Double-check new APIs for rate limiting and authorization.
- Run security checks on dependencies (e.g., `pip install pip-audit && pip-audit`) and document remediation plans.

## Contributor Rewards Model

- 50% of monthly net revenue is allocated to contributors; rewards are event-sourced (`RewardEvent`) and snapshotted monthly (`MonthlyRewardSnapshot` + `Payout`).
- Ledger is append-only; use compensating events for corrections.
- Recalculate payouts deterministically with `python manage.py calc_monthly_rewards <YYYY-MM> --revenue-cents=... --costs-cents=... --dry-run` (or `make rewards-dry-run`).
- Publish the CSV + hash produced by the management command for transparent audits.

## Helpful Commands

```bash
# Run tests
python manage.py test

# Seed demo data
python manage.py seed_demo

# Refresh SoulMatch profiles/scores
python manage.py refresh_soulmatch_profiles
python manage.py rebuild_soulmatch_scores

# Generate OpenAPI schema (example)
python manage.py generateschema --format openapi --outfile schema.yaml

# Start realtime gateway (from services/realtime)
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Need Help?

- Open a GitHub Discussion or issue with the `question` label.
- Tag maintainers in issues when you are blocked.
- Share logs, stack traces, and reproduction steps whenever you ask for help—it speeds up triage.

We are grateful for your contributions. Welcome to the selflink-backend community!
