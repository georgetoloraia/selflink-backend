PYTHON ?= python3
MANAGE := $(PYTHON) manage.py
PERIOD ?= $(shell date +%Y-%m)
MONTH ?= $(PERIOD)
REVENUE ?= 0
COSTS ?= 0
OUT ?= ./tmp/payout.csv

COMPOSE ?= $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")
COMPOSE_BASE ?= infra/compose.yaml
COMPOSE_HOST ?= infra/compose.host.yaml
COMPOSE_FILES ?= $(COMPOSE_BASE)
COMPOSE_CMD = $(COMPOSE) $(foreach f,$(COMPOSE_FILES),-f $(f))

HEALTHCHECK_API = python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/docs/')"
HEALTHCHECK_ASGI = python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/api/docs/')"
HEALTHCHECK_REALTIME = python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health')"

.PHONY: install migrate runserver celery-worker celery-beat compose-up compose-down up up-realtime test lint rewards-dry-run infra-up infra-down infra-logs infra-migrate infra-superuser snapshot-month
.PHONY: infra-up-local infra-up-host infra-down-local infra-down-host
.PHONY: infra-status infra-status-strict

install:
	$(PYTHON) -m pip install -r requirements.txt

migrate:
	$(MANAGE) migrate

runserver:
	$(MANAGE) runserver 0.0.0.0:8000

celery-worker:
	celery -A core worker -l info

celery-beat:
	celery -A core beat -l info

compose-up:
	$(COMPOSE_CMD) up -d --build

up:
	$(COMPOSE_CMD) up -d --build

up-realtime:
	$(COMPOSE_CMD) up -d --build

compose-down:
	$(COMPOSE_CMD) down

test:
	@if command -v pytest >/dev/null 2>&1; then pytest; else $(MANAGE) test; fi

lint:
	@if command -v ruff >/dev/null 2>&1; then ruff check .; else echo "ruff not installed; pip install ruff to run lint"; fi

rewards-dry-run:
	$(MANAGE) calc_monthly_rewards $(PERIOD) --revenue-cents=$(REVENUE) --costs-cents=$(COSTS) --dry-run

infra-up:
	$(COMPOSE_CMD) up -d --build

infra-down:
	$(COMPOSE_CMD) down

infra-logs:
	$(COMPOSE_CMD) logs -f --tail=100

infra-migrate:
	$(COMPOSE_CMD) exec api python manage.py migrate

infra-superuser:
	$(COMPOSE_CMD) exec api python manage.py createsuperuser

snapshot-month:
	$(COMPOSE_CMD) exec api python manage.py contrib_rewards_snapshot_month --month $(MONTH)

infra-status:
	@$(COMPOSE_CMD) ps
	@check() { label=$$1; shift; if "$$@" >/dev/null 2>&1; then echo "$$label: ok"; else echo "$$label: not ready"; return 1; fi; }; \
		check "api" $(HEALTHCHECK_API) || true; \
		check "asgi" $(HEALTHCHECK_ASGI) || true; \
		check "realtime" $(HEALTHCHECK_REALTIME) || true

infra-status-strict:
	@$(COMPOSE_CMD) ps
	@check() { label=$$1; shift; if "$$@" >/dev/null 2>&1; then echo "$$label: ok"; else echo "$$label: not ready"; return 1; fi; }; \
		status=0; \
		check "api" $(HEALTHCHECK_API) || status=1; \
		check "asgi" $(HEALTHCHECK_ASGI) || status=1; \
		check "realtime" $(HEALTHCHECK_REALTIME) || status=1; \
		exit $$status

infra-up-local:
	@$(MAKE) infra-up COMPOSE_FILES="$(COMPOSE_BASE)"
	@$(MAKE) infra-status COMPOSE_FILES="$(COMPOSE_BASE)"

infra-down-local:
	@$(MAKE) infra-down COMPOSE_FILES="$(COMPOSE_BASE)"

infra-up-host:
	@set -e; \
	ENV_FILE="infra/.env"; \
	if [ ! -f "$$ENV_FILE" ]; then \
		echo "infra-up-host: missing infra/.env (copy infra/.env.example -> infra/.env)"; \
		exit 1; \
	fi; \
	get_env() { \
		awk -v key="$$1" ' \
			/^[[:space:]]*#/ || /^[[:space:]]*$$/ { next } \
			{ \
				line=$$0; \
				sub(/^[[:space:]]*/, "", line); \
				split(line, parts, "="); \
				k=parts[1]; \
				if (k != key) next; \
				val = substr(line, index(line, "=") + 1); \
				sub(/[[:space:]]*#.*$$/, "", val); \
				gsub(/^[[:space:]]+|[[:space:]]+$$/, "", val); \
				print val; \
			} \
		' "$$ENV_FILE" | tail -n 1; \
	}; \
	strip() { echo "$$1" | sed -e 's/^"//' -e 's/"$$//' -e "s/^'//" -e "s/'$$//"; }; \
	secret=$$(strip "$$(get_env DJANGO_SECRET_KEY)"); \
	if [ -z "$$secret" ]; then echo "infra-up-host: DJANGO_SECRET_KEY must be set in infra/.env"; exit 1; fi; \
	debug=$$(strip "$$(get_env DJANGO_DEBUG)"); \
	if echo "$$debug" | grep -Eiq '^(true|1|yes|on)$$'; then echo "infra-up-host: DJANGO_DEBUG must be false"; exit 1; fi; \
	hosts=$$(strip "$$(get_env DJANGO_ALLOWED_HOSTS)"); \
	if [ -z "$$hosts" ] || [ "$$hosts" = "*" ]; then \
		echo "infra-up-host: DJANGO_ALLOWED_HOSTS must be set (comma-separated hosts)"; \
		exit 1; \
	fi; \
	if echo "$$hosts" | grep -Eiq '(^|,)[[:space:]]*(localhost|127\\.0\\.0\\.1|10\\.0\\.2\\.2)[[:space:]]*(,|$$)'; then \
		echo "infra-up-host: DJANGO_ALLOWED_HOSTS must not include localhost/127.0.0.1/10.0.2.2 in host mode"; \
		exit 1; \
	fi; \
	dburl=$$(strip "$$(get_env DATABASE_URL)"); \
	if [ -z "$$dburl" ]; then echo "infra-up-host: DATABASE_URL must be set"; exit 1; fi; \
	if echo "$$dburl" | grep -Eiq '://([^@/]*@)?(localhost|127\\.0\\.0\\.1)(:|/|$$)'; then \
		echo "infra-up-host: DATABASE_URL must use Docker hostnames (pgbouncer/postgres), not localhost"; \
		exit 1; \
	fi; \
	check_no_localhost_url() { \
		name="$$1"; value="$$2"; \
		if [ -n "$$value" ] && echo "$$value" | grep -Eiq '://([^@/]*@)?(localhost|127\\.0\\.0\\.1)(:|/|$$)'; then \
			echo "infra-up-host: $$name must not use localhost/127.0.0.1 inside Docker"; \
			exit 1; \
		fi; \
	}; \
	realtime_secret=$$(strip "$$(get_env REALTIME_JWT_SECRET)"); \
	jwt_key=$$(strip "$$(get_env JWT_SIGNING_KEY)"); \
	if [ -z "$$realtime_secret" ] && [ -z "$$jwt_key" ]; then \
		echo "infra-up-host: REALTIME_JWT_SECRET (or JWT_SIGNING_KEY fallback) must be set"; \
		exit 1; \
	fi; \
	if [ -z "$$realtime_secret" ] && [ -n "$$jwt_key" ]; then \
		echo "infra-up-host: WARNING: REALTIME_JWT_SECRET is empty; using JWT_SIGNING_KEY fallback"; \
	fi; \
	check_no_localhost_url CELERY_BROKER_URL "$$(strip "$$(get_env CELERY_BROKER_URL)")"; \
	check_no_localhost_url CELERY_RESULT_BACKEND "$$(strip "$$(get_env CELERY_RESULT_BACKEND)")"; \
	check_no_localhost_url REDIS_URL "$$(strip "$$(get_env REDIS_URL)")"; \
	check_no_localhost_url PUBSUB_REDIS_URL "$$(strip "$$(get_env PUBSUB_REDIS_URL)")"; \
	rate=$$(strip "$$(get_env RATE_LIMITS_ENABLED)"); \
	if [ "$$rate" != "true" ]; then \
		echo "infra-up-host: WARNING: RATE_LIMITS_ENABLED is not true (set to true for host mode)"; \
	fi
	@$(MAKE) infra-up COMPOSE_FILES="$(COMPOSE_BASE) $(COMPOSE_HOST)"
	@echo "infra-up-host: stack started on localhost ports (8000/8001/8002/8080)."
	@echo "infra-up-host: next steps -> make infra-migrate, then start Cloudflare Tunnel or reverse proxy."
	@$(MAKE) infra-status COMPOSE_FILES="$(COMPOSE_BASE) $(COMPOSE_HOST)"

infra-down-host:
	@$(MAKE) infra-down COMPOSE_FILES="$(COMPOSE_BASE) $(COMPOSE_HOST)"
