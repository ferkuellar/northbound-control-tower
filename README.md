# Northbound Control Tower

Northbound Control Tower is an enterprise-oriented multicloud operational intelligence platform for cloud inventory, FinOps diagnostics, governance analysis, observability readiness, HA/DR readiness, and executive cloud assessments.

Phase 0 establishes a modular monolith foundation. It intentionally avoids Kubernetes, microservices, event buses, auto-remediation, realtime systems, advanced RBAC, and broad cloud scope.

## Initial Scope

- Clouds: AWS and OCI only.
- Findings: idle compute, public exposure, missing tags, unattached volumes, observability gaps.
- AI features: executive summaries, technical assessments, remediation recommendations.
- Backend: FastAPI, PostgreSQL, Redis, Celery, SQLAlchemy, Alembic-ready structure.
- Frontend: Next.js, TailwindCSS, Apache ECharts-ready dependency.
- Observability: Prometheus, Grafana, OpenTelemetry-ready settings.

## Architecture Flow

Cloud Accounts -> Inventory Collectors -> Resource Normalization -> Findings Engine -> Risk Scoring -> AI Context Builder -> Claude/OpenAI Analysis -> Executive Reports & Dashboards

## Quick Start

```bash
make setup
make up
```

Services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

Default Grafana credentials are `admin` / `admin` for local development only. Change them in `.env` for shared environments.

## Validation

```bash
make compose-config
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/redis
curl http://localhost:8000/api/v1/status
```

## Development Standards

- Keep the backend a modular monolith until operational pressure proves otherwise.
- Normalize all provider resources before findings, scoring, AI, or reports consume them.
- Keep AWS/OCI-specific logic inside `backend/collectors`.
- Keep deterministic findings ahead of AI reasoning.
- Never place cloud credentials, AI keys, database passwords, or tokens in source control.

See `docs/architecture.md`, `docs/development.md`, and `docs/audit-phase-0.md`.
