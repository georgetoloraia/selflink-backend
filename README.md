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
- Docs: [`docs/coin/WALLET.md`](docs/coin/WALLET.md), [`docs/coin/TECHNICAL_REVIEW.md`](docs/coin/TECHNICAL_REVIEW.md), [`docs/PAYMENTS_IPAY.md`](docs/PAYMENTS_IPAY.md), [`docs/PAYMENTS_STRIPE.md`](docs/PAYMENTS_STRIPE.md), [`docs/PAYMENTS_BTCPAY.md`](docs/PAYMENTS_BTCPAY.md), [`docs/PAYMENTS_IAP.md`](docs/PAYMENTS_IAP.md), [`docs/GIFTS.md`](docs/GIFTS.md), [`docs/GIFTS_MEDIA_SPEC.md`](docs/GIFTS_MEDIA_SPEC.md), [`docs/GIFTS_SLC_PRICING.md`](docs/GIFTS_SLC_PRICING.md), [`docs/FEED_GIFTS.md`](docs/FEED_GIFTS.md)


1. [`START_HERE.md`](START_HERE.md)
2. [`docs/WHY_THIS_STACK.md`](docs/WHY_THIS_STACK.md)
3. [`docs/coin/WALLET.md`](docs/coin/WALLET.md)
4. [`CONTRIBUTOR_REWARDS.md`](CONTRIBUTOR_REWARDS.md)
5. [`docs/RUNBOOK.md`](docs/RUNBOOK.md)
6. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – High-level system layout and boundaries
7. [`docs/architecture/domains.md`](docs/architecture/domains.md) – Which modules are allowed to depend on which
8. [`apps/contrib_rewards/`](apps/contrib_rewards/) – The trust anchor (append-only ledger)
9. [`apps/core/`](apps/core/) – Identity, social graph, permissions
10. [`apps/mentor`](apps/mentor) / [`apps/astro`](apps/astro) / [`apps/matching/`](apps/matching/) – Optional intelligence layer
11. [`infra/`](infra/) – How the system runs in Docker / production

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
- `make coin-invariant-check` (verifies SLC ledger invariants; safe to run locally/host)
- Optional search stack: `docker compose -f infra/compose.yaml --profile search up -d`
- For more, see [`README_for_env.md`](README_for_env.md), [`docker_guide.md`](docker_guide.md), or [`docs/WHY_THIS_STACK.md`](docs/WHY_THIS_STACK.md)

Note: Docker Compose reads `infra/.env`; the root `.env` is only for non-Docker runs. Docker Compose interpolates `$VAR` in `infra/.env`, so escape literal `$` as `$$`. Inside containers, `localhost` does not point to other services; use Docker hostnames like `pgbouncer`, `redis`, and `opensearch`.

## License
Open source. See LICENSE.
