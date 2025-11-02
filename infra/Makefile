COMPOSE = docker compose -f infra/compose.yaml

.PHONY: up down logs migrate createsuperuser

up:
	$(COMPOSE) up -d --build

logs:
	$(COMPOSE) logs -f

down:
	$(COMPOSE) down --remove-orphans

migrate:
	$(COMPOSE) exec api python manage.py migrate

createsuperuser:
	$(COMPOSE) exec api python manage.py createsuperuser
