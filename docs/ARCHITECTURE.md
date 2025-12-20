# SelfLink Backend Architecture

This backend is split into clear domains so heavy/variable work can be isolated and audited cleanly.

See also:
- `docs/architecture/domains.md`
- `docs/architecture/diagram.md`
- `docs/DATA_RETENTION.md`

## Domains
- **Identity & Social (apps.users, apps.profile, apps.social, apps.messaging, apps.notifications)**  
  Authentication, identity, social graph, messaging, and notification fanout. PII is anchored in the user models with a dedicated `UserPII` container for sensitive fields to enable future row-level isolation.
- **AI Mentor (apps.mentor, apps.ai)**  
  Conversational mentor endpoints. HTTP views stay thin; LLM calls are executed via Celery tasks and can later stream via SSE/Channels.
- **Astro & Matching (apps.astro, apps.matrix, apps.matching)**  
  Deterministic astrology calculations, natal chart data, and soulmatch compatibility logic. Results are cacheable by birth data + rules version, and long-running work is offloaded to Celery tasks.
- **Rewards & Audit (apps.contrib_rewards)**  
  Append-only contributor reward ledger (RewardEvent), monthly snapshots (MonthlyRewardSnapshot), and payout calculations (Payout). Exposes reproducible CSV + hashes for public audit and dispute windows.
- **Payments (apps.payments)**  
  Subscription/billing flows separate from contributor rewards.
- **Search/Feed/Reco (apps.search, apps.feed, apps.reco)**  
  Query/indexing heavy paths that already rely on background tasks.

## Cross-cutting Practices
- Keep HTTP handlers boring and thin; push heavy/variable latency work to Celery tasks.
- Default DRF pagination and throttling; Redis-backed caches/rate limits for hot paths.
- Prefer append-only/auditable data for rewards and moderation; use select_related/prefetch to avoid N+1s.
- Deterministic scripts (e.g., monthly reward calculator) must be dry-runnable and emit hashes/CSV for verification.
- Security/privacy: avoid logging request bodies, isolate PII, and document retention policies alongside BYO LLM keys.
