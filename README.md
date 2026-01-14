# SelfLink - Full opensource unification

click for more [`WHAT-IS-SELFLINK.md`](WHAT-IS-SELFLINK.md)

## How to contribute
There are three simple ways to help:
1) Backend (Django / DRF): See [`CONTRIBUTING.md`](CONTRIBUTING.md)
2) Mobile (React Native / Expo): https://github.com/georgetoloraia/selflink-mobile
3) Architecture / design feedback: Open an issue — no code required
If you’re new, start with a good first issue.

## Contributor rewards (short version)
- 50% of future net platform revenue is reserved for contributors
- Contributions are tracked as immutable RewardEvents
- Rewards are calculated monthly using deterministic rules
- Corrections happen via new events, never by rewriting history
Full details: [`CONTRIBUTOR_REWARDS.md`](CONTRIBUTOR_REWARDS.md)

## SLC (SelfLink Coin) — internal USD credits
- Off-chain only: `1 SLC = 1 USD` (integer cents); no withdrawals to fiat/crypto
- Every user gets an SLC account automatically
- P2P transfers and internal spending are supported with transfer fees
- API (under `/api/v1/coin/`): `balance`, `ledger`, `transfer`, `spend`

FOR MORE Click [`wallet.md`](docs/wallet.md)


1. [`RUNBOOK.md`](docs/RUNBOOK.md)
2. [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) – High-level system layout and boundaries
3. [`domains.md`](docs/architecture/domains.md) – Which modules are allowed to depend on which
4. [`apps/contrib_rewards/`](apps/contrib_rewards/) – The trust anchor (append-only ledger)
5. [`apps/core/`](apps/core/) – Identity, social graph, permissions
6. [`apps/mentor`](apps/mentor) / [`apps/astro`](apps/astro) / [`apps/matching/`](apps/matching/) – Optional intelligence layer
7. [`infra/`](infra/) – How the system runs in Docker / production
8. [`docs/WHY_THIS_STACK.md`](docs/WHY_THIS_STACK.md)

You do **not** need to understand everything to contribute.
Most contributors work in a single domain.

For questions or collaboration, join the Discord: https://discord.gg/GQdQagsw

## Quickstart (backend)
- Prereq (Ubuntu/Debian): `sudo apt-get install -y docker-compose-plugin`
- Clone the repo and copy `infra/.env.example` to `infra/.env` (keep `$$` escapes for Compose)
- `make infra-up-local` (starts api + asgi + worker + realtime + postgres + redis + pgbouncer + media)
- `make infra-migrate`
- `make infra-superuser`
- `make infra-status` (informational health check)
- `make infra-status-strict` (fails if api/asgi/realtime are not healthy)
- Optional search stack: `docker compose -f infra/compose.yaml --profile search up -d`
- For more, see [`README_for_env.md`](README_for_env.md), [`docker_guide.md`](docker_guide.md), or [`docs/WHY_THIS_STACK.md`](docs/WHY_THIS_STACK.md)

Note: Docker Compose reads `infra/.env`; the root `.env` is only for non-Docker runs. Docker Compose interpolates `$VAR` in `infra/.env`, so escape literal `$` as `$$`. Inside containers, `localhost` does not point to other services; use Docker hostnames like `pgbouncer`, `redis`, and `opensearch`.

## License
Open source. See LICENSE.
