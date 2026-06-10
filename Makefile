GIT_SHA ?= $(shell git rev-parse --short HEAD)

.PHONY: setup up down restart logs ps backend-test backend-lint frontend-lint compose-config clean build deploy rollback

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

build:
	GIT_SHA=$(GIT_SHA) docker compose build

deploy:
	GIT_SHA=$(GIT_SHA) docker compose up -d

rollback:
	@test -n "$(GIT_SHA)" || (echo "Set GIT_SHA=<previous-sha> to rollback" && exit 1)
	GIT_SHA=$(GIT_SHA) docker compose up -d
