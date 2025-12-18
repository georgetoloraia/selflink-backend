PYTHON ?= python3
MANAGE := $(PYTHON) manage.py
PERIOD ?= $(shell date +%Y-%m)
REVENUE ?= 0
COSTS ?= 0
OUT ?= ./tmp/payout.csv

.PHONY: install migrate runserver celery-worker celery-beat compose-up compose-down test lint rewards-dry-run

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

compose-down:
	docker compose -f infra/compose.yaml down

test:
	$(MANAGE) test

lint:
	@if command -v ruff >/dev/null 2>&1; then ruff check .; else echo "ruff not installed; pip install ruff to run lint"; fi

rewards-dry-run:
	$(MANAGE) calc_monthly_rewards $(PERIOD) --revenue-cents=$(REVENUE) --costs-cents=$(COSTS) --dry-run
