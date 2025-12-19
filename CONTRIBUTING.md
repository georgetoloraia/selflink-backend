# Contributing to SelfLink

Quickstart
- Copy `.env.example` to `.env`
- Install dev tooling: `pip install -r requirements-dev.txt`
- `make up`
- `make migrate`
- `make test`

How to run tests
- `make test` (pytest)
- `make lint` (ruff)
- `pre-commit install` to enable local checks

How to open PRs
- Fork or branch, make focused changes with tests, then open a pull request explaining the change and impact.

Good first issues
- Look for labels like `good first issue` or `help wanted`.

Architecture
- Domain policy: `docs/architecture/domains.md`
- Diagram: `docs/architecture/diagram.md`

RFCs
- Use `docs/rfc/template.md` for proposals that impact domains, data models, or infra.
