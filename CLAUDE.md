# Northbound Control Tower

## Stack

- Backend: FastAPI + Celery + PostgreSQL + Redis (Python 3.12)
- Frontend: Next.js 16 + TypeScript + TailwindCSS
- Infra: Docker Compose (make up)

## Comandos clave

make up              # levantar stack completo
make backend-test    # pytest
make backend-lint    # ruff check
docker compose run --rm backend python scripts/seed_demo_data.py

## Convenciones

- Feature flags en core/config.py, nunca hardcodeados en lógica
- Credenciales: siempre encrypt_credential() — nunca plaintext
- Migraciones: cd backend && alembic revision --autogenerate -m "descripción"
- PROMPT_VERSION: incrementar en cada cambio a ai/prompts.py
- Tests: un archivo por módulo en backend/tests/

## Prioridad de sprint actual

Ver roadmap — atacar en orden: #27 → #9 → #24 → #25 → #26 → #29 → #30
