# Contributing to SelfLink

Quickstart
- Docker: copy `infra/.env.example` to `infra/.env`
- Local: copy `.env.example` to `.env`
- Install dev tooling: `pip install -r requirements-dev.txt`
- `make infra-up-local`
- `make infra-migrate`
- `make test`

How to run tests
Canonical runner is **pytest** (configured via `pytest.ini` with `core.settings.test`).
- Full suite: `pytest`
- Coin-only: `pytest apps/coin/tests`
- Stripe webhook coin test: `pytest tests/test_payments_webhook_coin.py`
- SLC invariants: `python manage.py coin_invariant_check` (or `make coin-invariant-check`)
- `make test` runs `pytest`
- `make lint` (ruff)
- `pre-commit install` to enable local checks
Notes:
- Tests are designed to be offline; Stripe webhook tests use local payloads/signatures only.

How to open PRs
- Fork or branch, make focused changes with tests, then open a pull request explaining the change and impact.

Good first issues
- Look for labels like `good first issue` or `help wanted`.

Architecture
- Domain policy: `docs/architecture/domains.md`
- Diagram: `docs/architecture/diagram.md`

RFCs
- Use `docs/rfc/template.md` for proposals that impact domains, data models, or infra.
