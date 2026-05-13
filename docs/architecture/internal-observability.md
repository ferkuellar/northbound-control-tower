# Internal Observability

## Purpose

Northbound Control Tower observes its own platform runtime before adding customer-scale observability integrations. Phase 11 adds backend metrics, structured logs, request correlation, OpenTelemetry tracing foundation, Celery task metrics, Prometheus scraping, and a Grafana platform overview dashboard.

## Metrics Strategy

The backend exposes Prometheus metrics at `GET /metrics`.

HTTP metrics:

- `http_requests_total`
- `http_request_duration_seconds`
- `http_requests_in_progress`
- `http_exceptions_total`

Platform metrics:

- inventory scan counts, failures, duration, and resources discovered
- findings run counts, duration, created and updated findings
- scoring run counts and duration
- AI analysis counts, failures, and duration
- report generation counts, failures, and duration
- Celery task starts/completions/failures and duration

Labels intentionally avoid tenant IDs, user IDs, resource IDs, request IDs, JWTs, full URLs, or cloud account IDs.

## Logging Strategy

Backend logs use structured JSON when `LOG_FORMAT=json`.

Required fields include:

- `timestamp`
- `level`
- `service`
- `environment`
- `logger`
- `message`
- `request_id`
- `trace_id`
- `span_id`

The formatter redacts obvious secret fields and credential-like values before serialization.

## Tracing Strategy

OpenTelemetry tracing is controlled by:

- `OBSERVABILITY_ENABLED`
- `OTEL_TRACING_ENABLED`
- `OTEL_SERVICE_NAME`
- `OTEL_EXPORTER_OTLP_ENDPOINT`

Instrumentation covers FastAPI, SQLAlchemy, Redis, requests, HTTPX, and selected business operations. The Docker Compose stack includes an OTLP collector that currently exports to debug logs. Grafana Tempo or another trace backend can be added later without changing application spans.

## Prometheus Setup

Prometheus scrapes:

- itself
- backend `http://backend:8000/metrics`

The production deployment must keep `/metrics` private through network policy, reverse proxy controls, or a private endpoint.

## Grafana Dashboard

The provisioned dashboard is `Northbound Control Tower - Platform Overview`.

It includes:

- HTTP request rate
- HTTP latency p95
- HTTP error rate
- inventory scans and duration
- findings runs and created/updated counts
- scoring calculations
- AI latency/errors
- report generation latency/errors
- backend uptime

## OpenTelemetry Collector

Compose includes `otel-collector` using `infrastructure/monitoring/otel/otel-collector-config.yml`.

The collector accepts OTLP on:

- `4317` gRPC
- `4318` HTTP

Phase 11 does not add Jaeger or Tempo; it prepares a clean collector boundary for future trace storage.

## Frontend Diagnostics

The Next.js app includes a global error boundary for safe user-facing failures. It avoids logging sensitive payloads and only emits minimal development diagnostics.

## Security Considerations

- Metrics do not include tenant IDs, user IDs, JWTs, secrets, or raw provider payloads.
- Logs redact obvious secrets and credential-shaped values.
- Traces must not include API keys, cloud credentials, private keys, full prompts, raw cloud payloads, or JWT tokens.
- `/metrics` is unauthenticated for local Docker only and must be restricted in production.

## Known Limitations

- Traces are collected but not persisted to a trace backend in Phase 11.
- Celery task metrics are process-local and exposed only if a future worker metrics endpoint is added or tasks execute in the backend process.
- Metrics are platform-level, not tenant-level, by design.

## Future Improvements

- Add Grafana Tempo for trace search.
- Add alert rules after operational thresholds are understood.
- Add structured log shipping to a controlled destination.
- Add worker metrics endpoint or Pushgateway if background workers become long-lived and distributed.
