COMPOSE ?= docker compose
COMPOSE_FILE ?= compose.yaml

.PHONY: up down logs migrate createsuperuser

up:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build

logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f

down:
	$(COMPOSE) -f $(COMPOSE_FILE) down --remove-orphans

migrate:
	$(COMPOSE) -f $(COMPOSE_FILE) exec api python manage.py migrate

createsuperuser:
	$(COMPOSE) -f $(COMPOSE_FILE) exec api python manage.py createsuperuser
