# Architecture Summary

Northbound Control Tower starts as a modular monolith with clear internal package boundaries. This keeps deployment simple while preserving the option to extract modules later if usage, team ownership, or scaling pressure justifies it.

Cloud Accounts -> Inventory Collectors -> Resource Normalization -> Findings Engine -> Risk Scoring -> AI Context Builder -> Claude/OpenAI Analysis -> Executive Reports & Dashboards

## Backend Modules

- `api`: FastAPI application, routers, health endpoints.
- `core`: configuration, logging, database, shared infrastructure wiring.
- `auth`: future authentication boundary; intentionally minimal in Phase 0.
- `models`: SQLAlchemy entities and shared domain enums.
- `collectors`: AWS/OCI collection and cloud-agnostic normalization.
- `findings`: deterministic finding rules.
- `scoring`: risk scoring policies.
- `ai`: AI context construction and provider adapters.
- `reports`: executive and technical report assembly.
- `workers`: Celery application and background jobs.
- `services`: application orchestration services.

## Normalized Resource Contract

```json
{
  "provider": "aws",
  "resource_type": "compute",
  "resource_id": "i-123",
  "region": "us-east-1",
  "name": "api-node-1",
  "tags": {"owner": "platform"},
  "risk_score": 20,
  "metadata": {}
}
```

Provider-specific details belong in `metadata` only when needed for diagnostics. Rule code must not branch on raw AWS or OCI SDK response shapes.

## Phase 0 Boundaries

Included: Docker Compose, FastAPI health/readiness/metrics, Next.js dashboard shell, PostgreSQL, Redis, Celery worker, Prometheus, and Grafana.

Excluded: Kubernetes, microservices, Kafka, event buses, service mesh, advanced RBAC, realtime systems, and autonomous remediation.
