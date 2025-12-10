FILE: README_UPDATE_TASK_SELF_LINK_BACKEND.txt
TITLE: Update selflink-backend README.md with full backend usage & contribution guide

GOAL:
Extend (not replace) the existing README.md in the selflink-backend repo so that it clearly explains:
- What this backend is and what it does
- How to set it up from scratch (local & Docker)
- How to run it (manage.py, Docker Compose)
- How to work with the API (auth, versioning, key endpoints)
- How to contribute (fork, branch, PR, code style)
- How the new AI Mentor feature fits into the architecture

IMPORTANT GLOBAL RULES:
- Do NOT delete or overwrite useful existing content from README.md.
- Preserve current sections and add new structured sections around / below them.
- If something is outdated or clearly wrong, you may fix it, but do not remove large parts blindly.
- The README must be understandable for a new contributor who just cloned selflink-backend.

The target audience:
- Python/Django developers who want to run or contribute to the backend.
- They might not know the project, so onboarding must be step-by-step.

==================================================
1. README STRUCTURE TO ACHIEVE
==================================================

The updated README.md should roughly follow this structure:

1) Title & short pitch
2) High-level overview (what SelfLink backend does)
3) Tech stack & architecture
4) Requirements & prerequisites
5) Setup and installation (local + Docker)
6) Running the backend (dev mode)
7) Environment configuration (.env)
8) Database & migrations
9) API overview (auth, versioning, key apps)
10) AI Mentor feature overview (new)
11) Tests & quality
12) Contributing guide
13) License / credits (if applicable)

You can adapt the exact headings, but keep this logical flow.

==================================================
2. CONTENT REQUIREMENTS FOR EACH SECTION
==================================================

2.1. Title & Short Pitch
- Keep the existing project title (SelfLink Backend / selflink-backend).
- Under it add a 1–2 sentence description in English:
  - Example: "SelfLink is a social OS backend built with Django and Django REST Framework, providing auth, social graph, messaging, astro/matrix services, AI Mentor, payments, and more."

2.2. High-Level Overview
- Briefly explain what this backend powers:
  - User registration & auth (email + social providers)
  - Social features (posts, comments, messaging, feed)
  - Astro & matrix modules (personal charts, life matrix, matching)
  - AI Mentor (LLM-powered personal guide)
  - Payments, notifications, moderation, search, etc.
- One short bullet list describing each main app group is enough.

2.3. Tech Stack & Architecture
- Summarize the main technologies:
  - Python, Django, Django REST Framework
  - PostgreSQL (or DATABASE_URL-based DB)
  - Redis (Celery broker, pub/sub)
  - Celery (background tasks)
  - OpenSearch (if enabled)
  - Docker + docker-compose (infra/compose.yaml)
- Mention the main apps from settings (apps.users, apps.social, apps.messaging, apps.mentor, apps.astro, apps.matrix, etc.) briefly in bullets.

2.4. Requirements & Prerequisites
- List minimum versions / tools required:
  - Python (matching the project)
  - Docker & docker-compose (if using Docker workflow)
  - PostgreSQL & Redis (if running without Docker)
  - pip / virtualenv
- Mention that there are two main ways to run:
  - Local (venv + manage.py runserver)
  - Docker (docker-compose -f infra/compose.yaml up)

2.5. Setup & Installation (Local)
- Provide a step-by-step guide for local setup:
  1) Clone repo
     - `git clone ...`
     - `cd selflink-backend`
  2) Create and activate virtualenv
     - `python -m venv venv`
     - `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
  3) Install dependencies
     - `pip install -r requirements.txt`
  4) Create .env file or export environment variables (see next section)
  5) Run migrations
     - `python manage.py migrate`
  6) Create superuser (optional)
     - `python manage.py createsuperuser`
  7) Run dev server
     - `python manage.py runserver`

2.6. Setup & Installation (Docker)
- Describe Docker-based workflow using infra/compose.yaml:
  - `docker-compose -f infra/compose.yaml up -d`
  - Mention how to exec into api container:
    - `docker-compose -f infra/compose.yaml exec api bash`
  - Run migrations inside container:
    - `python manage.py migrate`
  - Collect static if needed:
    - `python manage.py collectstatic --noinput`
- Briefly mention which services run via compose (api, db, redis, etc.).

2.7. Environment Configuration (.env)
- Explain that settings read environment variables for:
  - DATABASE_URL
  - DJANGO_SECRET_KEY
  - DJANGO_DEBUG
  - DJANGO_ALLOWED_HOSTS
  - CELERY_BROKER_URL, CELERY_RESULT_BACKEND
  - OPENSEARCH_* variables
  - FEATURE_FLAGS (mentor_llm, soulmatch, payments, etc.)
  - SWISSEPH_DATA_PATH for astro data
- Give a minimal example .env snippet in README.

2.8. Database & Migrations
- Explain the migration workflow:
  - `python manage.py makemigrations`
  - `python manage.py makemigrations <app_name>` for per-app changes
  - `python manage.py migrate`
- Mention that the default DB is sqlite if DATABASE_URL is not set, but for production use Postgres.

2.9. API Overview
- Explain:
  - Base API path: `/api/v1/`
  - OpenAPI schema: `/api/schema/`
  - Docs: `/api/docs/`
- Mention main routers included in apps/core/api_router.py:
  - auth (apps.users)
  - social
  - messaging
  - mentor
  - astro
  - profile
  - matrix
  - media
  - payments
  - notifications
  - moderation
  - feed
  - reco
- Briefly describe how authentication works:
  - JWT via dj-rest-auth / SimpleJWT
  - Typical login/register endpoints (e.g. `/api/v1/auth/`...)

2.10. AI Mentor Feature (NEW SECTION)
- Add a section that describes the new AI Mentor backend:

  - What it is:
    - LLM-powered personal mentor for users.
    - Uses `/api/v1/mentor/chat/` and `/api/v1/mentor/history/` endpoints.
  - How to use in development:
    - With no LLM configured, the mentor returns a placeholder reply.
  - How to wire an actual LLM:
    - Mention env vars:
      - `MENTOR_LLM_BASE_URL` (OpenAI-compatible /v1/chat/completions endpoint)
      - `MENTOR_LLM_MODEL`
    - Example: running a local LLM via Ollama or vLLM (high-level, not too long).
  - Mention that persona prompts are loaded from:
    - `apps/mentor/persona/base_en.txt`, etc.
  - Note that MentorSession and MentorMessage can be inspected via Django admin.

2.11. Tests & Quality
- Explain how to run tests:
  - `pytest` (if pytest is used)
  - Or `python manage.py test`
- Mention that there are tests for mentor API:
  - `apps/mentor/tests/test_api.py`
- Encourage contributors to add tests for new features.

2.12. Contributing Guidelines
- Add a simple CONTRIBUTING-style section inside README (even if there is no CONTRIBUTING.md yet):
  - Steps:
    1) Fork the repo
    2) Create a feature branch:
       - `git checkout -b feature/my-change`
    3) Make changes and add tests
    4) Run tests locally (pytest or manage.py test)
    5) Create a Pull Request with a clear description
  - Coding style:
    - Follow existing Django app patterns.
    - Keep changes small and focused.
  - For mentor-related changes:
    - Try to keep AI prompts and configs in the appropriate files (persona txt, services, etc.).
    - Avoid hardcoding secrets or API keys.

2.13. License / Credits
- If README already has license info, keep it and do not remove.
- If not, add a small placeholder line (e.g. "License: TBD") ONLY if appropriate and consistent with the project.

==================================================
3. STYLE & LANGUAGE
==================================================

- Main README language: English.
- Keep the tone friendly, but concise and professional.
- Use Markdown headings (#, ##, ###), bullet lists, and code blocks.
- Prefer real command examples (copy-paste ready).

Do NOT:
- Overload README with overly long essays; keep things practical.
- Duplicate full architecture docs already present in docs/; you can link or briefly mention them if needed.

==================================================
4. IMPLEMENTATION NOTES FOR CODEX
==================================================

- Open README.md in the selflink-backend root.
- Read existing content first.
- Insert or extend sections according to this spec.
- Preserve any useful current content (project description, badges, etc.).
- Integrate new sections smoothly; don't just append a huge block at the very end without context.
- After editing, the README.md should:
  - still render valid Markdown,
  - be easy to navigate,
  - allow a new developer to:
    - install,
    - configure,
    - run,
    - and contribute to selflink-backend.

END OF FILE
