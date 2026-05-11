.PHONY: setup up down restart logs ps backend-test backend-lint frontend-lint compose-config clean

setup:
	cp -n .env.example .env

up:
	docker compose up --build

down:
	docker compose down

restart:
	docker compose down
	docker compose up --build

logs:
	docker compose logs -f

ps:
	docker compose ps

backend-test:
	docker compose run --rm backend python -m pytest

backend-lint:
	docker compose run --rm backend ruff check .

frontend-lint:
	docker compose run --rm frontend npm run lint

compose-config:
	docker compose config

clean:
	docker compose down -v
