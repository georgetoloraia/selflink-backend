# Domains and Boundaries

This document defines the domain split for SelfLink Backend and the import/dependency rules
that keep the system modular and safe to evolve.

## Domains

### Core Platform
Owns identity, profiles, social graph, messaging, payments, rewards, notifications, moderation,
configuration, and audit.

Typical apps today:
- apps.core
- apps.users
- apps.profile
- apps.social
- apps.messaging
- apps.payments
- apps.notifications
- apps.moderation
- apps.config
- apps.contrib_rewards

### Intelligence
Owns compute-heavy or variable logic: mentor chat, astrology, matching/recommendations,
search, and embeddings.

Typical apps today:
- apps.mentor
- apps.astro
- apps.matching
- apps.reco
- apps.search
- apps.ai
- apps.matrix

### Rewards
Rewards data is append-only and domain-owned by rewards; core uses public APIs or snapshots.

### Audit
Audit/event records are append-only and provide a public write interface for other domains.

## Dependency Rules

- Core MUST NOT import Intelligence service modules or task modules.
  - Examples of forbidden imports: apps.mentor.services.*, apps.astro.tasks.*, apps.matching.services.*
- Intelligence MAY read Core data via public model/query APIs, but MUST NOT mutate Core tables
  directly except via approved public interfaces (for example, creating audit events).
- Cross-domain communication for heavy work should use Celery tasks or explicit service interfaces.
- HTTP handlers should remain thin: validate inputs, persist requests, enqueue tasks, and return identifiers.

## Data Ownership

- Core is the source of truth for user identity, social graph, payments, and rewards ledger.
- Intelligence is the source of truth for computed outputs (mentor sessions/messages, astrology results,
  matching results, search indexes).
- Postgres is the system of record; caches are optional and derived.

