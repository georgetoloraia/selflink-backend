SELF­LINK — END-TO-END PROJECT BLUEPRINT (v1)
Date: 2025-10-29


================================================================================
PURPOSE
--------------------------------------------------------------------------------
This document is a step-by-step, well-structured specification and execution
guide for building SelfLink: a conscious social network that combines
AI Mentor, soul/energy awareness (astrology + matrix), and a healthy social
graph (posts, follows, likes, gifts, messaging). It is written to be readable
by humans and machine agents (LLMs) and to serve as a single source of truth
from idea → launch → scale.

Use this file as:
- Product brief + engineering spec
- Architecture plan + API contract (draft)
- Delivery roadmap + ops handbook
- Monetization model + basic forecasts


================================================================================
1) PROBLEM & OPPORTUNITY
--------------------------------------------------------------------------------
• People experience “connection scarcity” despite hyper-connectivity.
• Loneliness correlates with poor mental/physical health.
• Existing social apps optimize for attention, not awareness.
• Self-improvement apps are siloed (meditation OR coaching OR astrology),
  rarely integrated into a living social network with real relationships.

Opportunity: build a platform that centers awareness and real connection,
guided by an AI Mentor that knows the user’s energetic/psychological profile
and fosters healthy social behaviors.


================================================================================
2) VISION & PHILOSOPHY
--------------------------------------------------------------------------------
Mission: Reconnect humanity — not through data, but through consciousness.

Principles:
• Awareness over noise
• Connection over competition
• Energy over ego
• Wisdom through technology
• Privacy as sacred trust
• Simplicity as sacred design
• Evolution through empathy

Product Pillars (4):
1) SELF  — AI Mentor, daily reflections, tasks, growth tracking
2) LINK  — Resonant matching (SoulMatch), DM, real friendships/partners
3) MATRIX— Energetic profile: astrology + numerology “matrix”
4) COMMUNITY — Healthy social graph: posts, comments, likes, gifts


================================================================================
3) UNIQUE DIFFERENTIATORS
--------------------------------------------------------------------------------
• AI Mentor with evolving personality (Dynamic Soul Engine) that adapts to the
  user’s matrix & emotions; short, empathic, non-judgmental guidance.
• Soul Frequency: compatibility score combining astro, matrix, behavior signals,
  and mentor feedback.
• 3D Life Matrix visualization (calm, meaningful; not gimmicky).
• Karma System: positive, prosocial behaviors are rewarded (not volume of posts).
• Marketplace for experts (psychologists, matrixologists, astrologers) with
  revenue share and verified credentials.


================================================================================
4) USER PERSONAS & JOBS-TO-BE-DONE
--------------------------------------------------------------------------------
Personas:
• Seeker (18–35): wants guidance, healing, meaningful relationships.
• Builder (25–45): wants to contribute wisdom, lead groups, monetize content.
• Companion (any age): wants calm social space, not noisy feeds.

Core JTBDs:
• “Help me understand myself” (insight + daily practice)
• “Help me connect with resonant people” (SoulMatch)
• “Give me a safe social environment to share and learn”
• “Keep me gently accountable to my growth path”


================================================================================
5) SCOPE — FEATURES (MVP → V1 → V2)
--------------------------------------------------------------------------------
MVP (0–3 months):
• Registration/login, user profiles
• Matrix/Astro basic profile (Sun/Moon/Ascendant + Life Path)
• AI Mentor v0 (rule-based + templated insights; daily tasks)
• Social basics: posts, comments, likes, follow
• DM (REST polling), notifications (in-app)
• Minimal feed (reverse chrono), media uploads (images), search (users only)
• Privacy & moderation primitives, Terms/Privacy pages
• Deploy single-region (EU), CDN enabled

V1 (3–9 months):
• AI Mentor v1 (hybrid rule-based + small LLM or hosted LLM; memory JSON)
• SoulMatch (compatibility scores, mutual discovery)
• Realtime messaging (WebSocket), push notifications
• Feed ranking (quality + relationship + recency)
• Gifts/tokens, wallet, subscriptions (Stripe)
• OpenSearch indices for users + posts
• Expert marketplace (curated), courses/practices module
• Observability stack, A/B testing flags, rate limiting

V2 (9–18 months):
• AI Mentor v2 (local LLM/finetune; voice mentor optional)
• Matrix/Astro deep sync (paid APIs + caching), 3D visualization
• Group chats & circles, events, advanced moderation
• Multi-region architecture (read replicas; edge cache)
• Sharding, CQRS feeds, fan-out-on-read for large creators
• Analytics warehouse (ClickHouse/BigQuery), cohort analysis
• Enterprise/Schools pilot (B2B2C)


================================================================================
6) SYSTEM ARCHITECTURE (HIGH LEVEL)
--------------------------------------------------------------------------------
Core Platform (Django/DRF):
• Auth, profiles, social, media, payments, notifications, moderation

Async Workers (Celery + Redis/Kafka):
• Feed fan-out, media processing (thumbnails/transcode/NSFW), search indexing,
  emails/push, recommendations, astro/matrix sync, analytics export

Realtime Gateway (FastAPI + WebSocket + Redis pub/sub):
• DM delivery, presence, typing, read-receipts

Search (OpenSearch/Elasticsearch):
• Users, posts (later: limited personal search for messages)

Media (S3-compatible + CDN):
• Presigned uploads from client; workers generate renditions

AI Layer:
• Mentor Core (rule-based + adapters), Memory store (per user JSON),
  optional hosted LLM initially; later local LLM (LLaMA/Mistral)

Data Warehouse:
• Event stream sink → analytics warehouse, dashboards

Observability:
• Prometheus + Grafana, Sentry, centralized logs


================================================================================
7) REPO & APP LAYOUT (MONOREPO)
--------------------------------------------------------------------------------
selflink/
  apps/
    users/            # auth, profiles, settings, privacy
    social/           # posts, comments, likes, follow, gifts
    messaging/        # threads, messages, attachments
    feed/             # timelines, ranking
    media/            # uploads, renditions, nsfw
    mentor/           # AI mentor core and sessions
    matrix/           # astro/matrix connectors & models
    search/           # indexing pipelines
    payments/         # wallet, subscriptions, gifts store
    notifications/    # in-app, push, email
    moderation/       # reports, enforcement
  services/
    realtime/         # FastAPI WS gateway
    reco/             # ranking workers
  core/
    settings/         # base.py, dev.py, prod.py
    urls.py, asgi.py, wsgi.py
  libs/
    idgen.py, utils, auth helpers
  infra/
    docker/, k8s/, compose.yaml
  tests/
  manage.py


================================================================================
8) DATA MODEL (SUMMARY)
--------------------------------------------------------------------------------
USERS
• User(id, handle, name, photo, birth_date/time/place, locale, flags)
• UserSettings(user, privacy, dm_policy, language)
• Block(user, target), Mute(user, target), Device(user, push_token)

SOCIAL
• Post(id, author_id, text, media[], visibility, created_at)
• Comment(id, post_id, author_id, text, parent_id, created_at)
• Like(user_id, target_type, target_id, created_at)
• Follow(follower_id, followee_id, created_at)
• Gift(id, sender_id, receiver_id, type, payload, created_at)
• Timeline(user_id, post_id, score, created_at)  # materialized feed

MESSAGING
• Thread(id, is_group, created_by)
• ThreadMember(thread_id, user_id, role, last_read_msg_id)
• Message(id, thread_id, sender_id, body, type, meta, created_at)

MEDIA
• MediaAsset(id, owner_id, s3_key, mime, width, height, duration, status)

MENTOR
• MentorProfile(user_id, tone, level, prefs JSON)
• MentorSession(id, user_id, question, answer, sentiment, created_at)
• DailyTask(id, user_id, task, due_date, status)

MATRIX
• AstroProfile(user_id, sun, moon, ascendant, planets JSON, aspects JSON, houses JSON)
• MatrixData(user_id, life_path, traits JSON)

PAYMENTS
• Plan(id, name, price, features JSON)
• Subscription(user_id, plan_id, status, period)
• Wallet(user_id, balance), GiftType(id, price, art)

MODERATION
• Report(id, reporter_id, target_type, target_id, reason, status)
• Enforcement(id, target_type, target_id, action, expires_at)


================================================================================
9) ID GENERATION & PAGINATION
--------------------------------------------------------------------------------
• Snowflake-like 64-bit IDs (time-ordered; libs/idgen.py)
• Cursor-based pagination everywhere (no page/limit for feed/messages)


================================================================================
10) API CONTRACT (DRAFT EXAMPLES)
--------------------------------------------------------------------------------
Auth:
  POST /api/v1/auth/register
  POST /api/v1/auth/login  → {{ access, refresh }}
  POST /api/v1/auth/refresh
Users:
  GET  /api/v1/users/{{id}}
  GET  /api/v1/users/search?q=...
  PATCH/PUT /api/v1/users/{{id}}
Posts:
  POST /api/v1/posts {{ text, media_ids[], visibility }}
  GET  /api/v1/posts/{{id}}
  GET  /api/v1/feed/home?cursor=...
  POST /api/v1/posts/{{id}}/like
Follows:
  POST /api/v1/users/{{id}}/follow
Messaging:
  POST /api/v1/threads
  GET  /api/v1/threads?cursor=...
  POST /api/v1/messages {{ thread_id, body }}
  GET  /api/v1/messages?thread_id=...&cursor=...
Mentor:
  POST /api/v1/mentor/ask {{ text }}
  GET  /api/v1/mentor/daily
Matrix:
  GET  /api/v1/matrix/profile  (create-on-read if missing)
  POST /api/v1/matrix/sync
Payments:
  GET  /api/v1/plans
  POST /api/v1/subscribe
Notifications:
  GET  /api/v1/notifications?cursor=...

Response example (feed item):
{{ "id": "sf_...", "author": {{ "id": "...", "handle": "giorgi" }},
  "text": "…", "media": [...], "liked": false, "likes": 12,
  "created_at": "2025-03-15T10:20:00Z" }}


================================================================================
11) AI MENTOR DESIGN
--------------------------------------------------------------------------------
GOALS
• Be a kind, concise, present companion. One insight or task per reply.
• Adapt tone to user: gentle / balanced / enthusiastic.
• Use user’s astro/matrix traits for framing, never fatalistic.

KERNEL (rule-based start):
• Detect intent/emotion keywords (“sad”, “anxious”, “goal”, “relationship”).
• Map to response templates with micro-coaching patterns.
• Always end with an actionable reflection (journal prompt or 5-min task).

MEMORY
• Per-user JSON memory (topics, wins, struggles, preferred tasks).
• Keep last N chats for context; summarize weekly into “Mentor Note”.

LEARNING LOOP
• After each session, update memory & trend (positive/neutral/negative).
• Adjust daily tasks based on completion & user feedback.

LOCAL LLM (phase 2)
• Host small LLM (e.g., 3–8B) with safety/guardrails + RAG from memory.
• Persona/config file (mentor_manifest.json) with tone/rules.

PROMPT SHAPE (example)
System: “You are SelfLink Mentor… Mission, tone, rules… User traits: Sun=X, Moon=Y, LifePath=Z. Never judge. One insight + one small task.”
User: “…question…”
Assistant: “…short reflection + task…”


================================================================================
12) MATRIX/ASTRO CONNECTORS
--------------------------------------------------------------------------------
• Providers: (choose) AstroAPI, Aztro, commercial astro SDKs, or internal compute.
• Sync on profile creation or user update; cache results (ETag-style).
• Minimal fields for MVP: Sun/Moon/Ascendant + selectable traits JSON.
• Matrix (numerology) compute locally: Life Path, core numbers, simple traits.
• Store raw provider payloads (for audit) and derived normalized fields.


================================================================================
13) FEED & RANKING
--------------------------------------------------------------------------------
• MVP: reverse chronological with lightweight boosts (friends, comments).
• V1 ranking score:
  score = recency * (w1*likes + w2*comments + w3*saves) * relationship_weight
• Explore creator downranking for spam, upweight posts with high karma comments.
• Fan-out-on-write with read-repair; fallback to fan-out-on-read for large creators.


================================================================================
14) MESSAGING & REALTIME
--------------------------------------------------------------------------------
• REST first (MVP); then WebSocket gateway (FastAPI + Redis pub/sub).
• Typing indicators, read receipts, presence.
• Media in DM via MediaAsset; throttled uploads; attachment virus-scan.
• Abuse prevention: rate limits, blocked users list enforcement.


================================================================================
15) SEARCH
--------------------------------------------------------------------------------
• OpenSearch indices: users (handle, name, bio), posts (text, lang, tags).
• Indexing pipeline via Celery consumers on post/user events.


================================================================================
16) MEDIA PIPELINE
--------------------------------------------------------------------------------
• Client → presigned S3 upload; DB stores metadata.
• Worker generates thumbnails, video transcodes; NSFW scan.
• CDN (Cloudflare) cache; signed URLs for premium content.


================================================================================
17) NOTIFICATIONS
--------------------------------------------------------------------------------
• In-app + push (FCM/APNs), email for critical events.
• Event-driven creators: like/follow/comment/message/mentor daily.
• User-level quiet hours, digest mode, unsubscribe map.


================================================================================
18) PAYMENTS & MONETIZATION
--------------------------------------------------------------------------------
TIERS
• Free: core feed, basic mentor, basic matrix
• Premium ($8–10/mo): Mentor+, deep insights, SoulMatch+, advanced filters, 3D matrix
• Gifts/Tokens: $1 per coin average; stickers, animations, blessed gifts
• Courses/Practices: revenue share with verified experts
• Marketplace fees: 10–20% take rate

REVENUE SCENARIOS (illustrative; blended ARPPU includes gifts/coins uplift):
Users   Paid%  Paid ARPU  Blended uplift  MRR           ARR
100k    10%    $8         +20%            ~$96k         ~$1.15M
1M      15%    $9         +30%            ~$1.755M      ~$21.1M
5M      20%    $10        +35%            ~$13.5M       ~$162M

COST BALLPARK (monthly; early single region):
• Infra (100k MAU): $3–8k (compute, DB, S3/CDN, search, observability)
• 1M MAU: $40–80k (multi-region, ops staff, heavier media/search)


================================================================================
19) PRIVACY, SECURITY, COMPLIANCE
--------------------------------------------------------------------------------
• Privacy by design: sensitive astro/matrix data scoped to user; explicit consent.
• GDPR/CCPA flows: data export/delete; audit logs for access to sensitive data.
• JWT rotation, device binding, IP risk scoring; 2FA optional.
• Content moderation: heuristics + ML + human review queue.
• Secrets in vault (SOPS/SealedSecrets); least privilege IAM.


================================================================================
20) OBSERVABILITY & SLOs
--------------------------------------------------------------------------------
• Metrics: request latency, error rates, queue lag, WS connections, feed build time.
• SLOs (initial): API p95 < 250ms; WS availability 99.9%; media processing < 2m p95.
• Alerting: on-call rotation, runbooks per service, outage comms template.


================================================================================
21) INFRA & DEPLOYMENT
--------------------------------------------------------------------------------
DEV (Docker Compose):
• Services: django, postgres, redis, minio (S3), opensearch, fastapi-rt, celery
• make up / make down scripts

PROD (Kubernetes):
• Separate pods for API, workers, realtime, search client
• Postgres managed (CloudSQL/RDS), Redis (ElastiCache/Upstash), S3 (Cloud), CDN
• Blue/green deploys via GitHub Actions; migrations gate; feature flags

ENV VARS (sample):
DJANGO_SETTINGS_MODULE=core.settings.prod
DATABASE_URL=postgres://...
REDIS_URL=redis://...
S3_BUCKET=selflink-media
OPENSEARCH_URL=https://...
JWT_SECRET=...
STRIPE_KEY=...
MENTOR_MODE=hybrid


================================================================================
22) DELIVERY ROADMAP (STEP-BY-STEP)
--------------------------------------------------------------------------------
PHASE 0 — FOUNDATION (2–4 weeks)
1. Create monorepo; settings split (base/dev/prod); libs/idgen.py.
2. apps: users, social (posts/likes/comments), media, notifications.
3. Auth (JWT), profiles, image upload (S3), reverse-chrono feed.
4. Basic admin, moderation primitives, Terms/Privacy pages.
5. CI (lint/test), docker-compose; deploy to single region.

PHASE 1 — MENTOR & MATRIX (4–6 weeks)
1. matrix: life-path compute + astro provider stub + caching.
2. mentor: rule-based core + daily tasks; per-user JSON memory.
3. endpoints: /mentor/ask, /mentor/daily, /matrix/profile, /matrix/sync.
4. notifications for mentor daily + gentle nudges.

PHASE 2 — SOCIAL GRAPH & DM (6–8 weeks)
1. follow, search users, profile pages.
2. messaging REST (threads/messages), then WS gateway.
3. in-app notifications; push integration; rate limiting.

PHASE 3 — MATCHING & RANKING (8–10 weeks)
1. SoulMatch v1: SoulScore (astro + matrix + light behavior).
2. feed ranking v1; OpenSearch indexing; spam safeguards.
3. gifts/tokens MVP; wallet; Stripe subscriptions.

PHASE 4 — POLISH & SCALE (ongoing)
1. observability hardening, error budgets, load tests.
2. expert marketplace beta; courses/practices module.
3. multi-region read replicas; CDN tuning; backup/restore drills.


================================================================================
23) TEAM & HIRING PLAN (MVP → V1)
--------------------------------------------------------------------------------
MVP core (4–6 people):
• 1 Tech Lead (Python/Django/Infra)
• 1 Backend Eng (social/feed/media)
• 1 Frontend Eng (React/Next)
• 1 AI/ML Eng (mentor core/memory)
• 1 Designer (brand/UI/3D matrix)
• 0.5 PM/Founder (vision + ops)

V1 expand (8–12):
• + Realtime/WS Eng, iOS/Android (Flutter), DevOps/SRE, Community Lead

Operating rituals:
• Weekly planning; Kanban board with Epics/Stories; docs-first culture.


================================================================================
24) RISK MATRIX & MITIGATIONS
--------------------------------------------------------------------------------
• Adoption risk → Seed with niche communities (spiritual tech, wellness).
• Safety risk → Strong moderation + report flows + rate limits.
• Infra cost risk → Media quotas, aggressive caching, remote storage tiers.
• Vendor risk (LLM/APIs) → Hybrid mentor core + local LLM path.
• Regulation risk → Clear consent, transparency, parental controls (if <18).


================================================================================
25) LAUNCH PLAN
--------------------------------------------------------------------------------
• Private alpha (100–500 users): mentors/experts + early adopters.
• Public beta (5k–20k): waitlist, referral codes, guided onboarding.
• Partnerships: wellness communities, spiritual leaders, psychologists.
• Content strategy: daily reflections, calm visuals, success stories.
• Metrics to watch: D1/D7 retention, mentor session count, healthy comment ratio,
  DM starts from SoulMatch, premium conversion %.


================================================================================
26) APPENDICES
--------------------------------------------------------------------------------
A) DEV QUICKSTART
  python -m venv venv && source venv/bin/activate
  pip install -r requirements.txt
  docker compose up -d
  python manage.py migrate
  python manage.py runserver

B) FEED SCORE (example formula)
  score = (1 / log(2 + age_hours)) *
          (1 + 0.5*likes + 1.2*comments + 0.8*saves) *
          relationship_weight

C) MENTOR RESPONSE TEMPLATE (short)
  • Empathic acknowledgement (1 sentence)
  • One reframing insight (1 sentence)
  • One tiny task (1 line) — “Try 3-minute breath check now.”

D) SOULMATCH (v1 inputs)
  • Astro: sun-moon-asc alignment (normalized)
  • Matrix: life path compatibility
  • Behavior: positivity/karma signals
  • Mentor note: growth focus overlap

E) SAMPLE .ENV (dev)
  DJANGO_DEBUG=1
  DATABASE_URL=postgres://postgres:postgres@localhost:5432/selflink
  REDIS_URL=redis://localhost:6379/0
  S3_ENDPOINT=http://localhost:9000
  S3_ACCESS_KEY=minio
  S3_SECRET_KEY=minio123

F) NON-GOALS (for now)
  • Long-form video hosting
  • Encrypted E2E chats
  • Open platform plugins


================================================================================
END OF BLUEPRINT
--------------------------------------------------------------------------------