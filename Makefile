PYTHON ?= python3
MANAGE := $(PYTHON) manage.py
PERIOD ?= $(shell date +%Y-%m)
MONTH ?= $(PERIOD)
REVENUE ?= 0
COSTS ?= 0
OUT ?= ./tmp/payout.csv

HEALTHCHECK_API = python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/docs/')"
HEALTHCHECK_ASGI = python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/docs/')"
HEALTHCHECK_REALTIME = python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health')"

.PHONY: install migrate runserver celery-worker celery-beat compose-up compose-down up up-realtime test lint rewards-dry-run infra-up infra-down infra-logs infra-migrate infra-superuser snapshot-month
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
	docker compose -f infra/compose.yaml up -d --build

up:
	docker compose -f infra/compose.yaml up -d --build

up-realtime:
	docker compose -f infra/compose.yaml up -d --build

compose-down:
	docker compose -f infra/compose.yaml down

test:
	@if command -v pytest >/dev/null 2>&1; then pytest; else $(MANAGE) test; fi

lint:
	@if command -v ruff >/dev/null 2>&1; then ruff check .; else echo "ruff not installed; pip install ruff to run lint"; fi

rewards-dry-run:
	$(MANAGE) calc_monthly_rewards $(PERIOD) --revenue-cents=$(REVENUE) --costs-cents=$(COSTS) --dry-run

infra-up:
	docker compose -f infra/compose.yaml up -d --build

infra-down:
	docker compose -f infra/compose.yaml down

infra-logs:
	docker compose -f infra/compose.yaml logs -f --tail=100

infra-migrate:
	docker compose -f infra/compose.yaml exec api python manage.py migrate

infra-superuser:
	docker compose -f infra/compose.yaml exec api python manage.py createsuperuser

snapshot-month:
	docker compose -f infra/compose.yaml exec api python manage.py contrib_rewards_snapshot_month --month $(MONTH)

infra-status:
	@docker compose -f infra/compose.yaml ps
	@check() { label=$$1; shift; if "$$@" >/dev/null 2>&1; then echo "$$label: ok"; else echo "$$label: not ready"; return 1; fi; }; \
		check "api" $(HEALTHCHECK_API) || true; \
		check "asgi" $(HEALTHCHECK_ASGI) || true; \
		check "realtime" $(HEALTHCHECK_REALTIME) || true

infra-status-strict:
	@docker compose -f infra/compose.yaml ps
	@check() { label=$$1; shift; if "$$@" >/dev/null 2>&1; then echo "$$label: ok"; else echo "$$label: not ready"; return 1; fi; }; \
		status=0; \
		check "api" $(HEALTHCHECK_API) || status=1; \
		check "asgi" $(HEALTHCHECK_ASGI) || status=1; \
		check "realtime" $(HEALTHCHECK_REALTIME) || status=1; \
		exit $$status
