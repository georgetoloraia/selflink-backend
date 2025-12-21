PYTHON ?= python3
MANAGE := $(PYTHON) manage.py
PERIOD ?= $(shell date +%Y-%m)
MONTH ?= $(PERIOD)
REVENUE ?= 0
COSTS ?= 0
OUT ?= ./tmp/payout.csv

.PHONY: install migrate runserver celery-worker celery-beat compose-up compose-down up up-realtime test lint rewards-dry-run infra-up infra-down infra-logs infra-migrate infra-superuser snapshot-month

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
	docker compose -f infra/compose.yaml --profile realtime up -d --build

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
