# Changelog

All notable changes to this project will be documented in this file.

This project follows a practical Keep a Changelog style. Version numbers and phase labels communicate product maturity, architecture milestones, and release readiness.

---

## [Unreleased]

### Added
- Async AI analysis execution: `POST /ai/analyze` now returns `202 Accepted` with `{analysis_id, status: "pending"}`; the provider call runs in a Celery worker. Clients poll `GET /ai/analyses/{id}` for the result.
- `AIAnalysisStatus.RUNNING` intermediate state to track in-progress Celery jobs.
- Baseline CI pipeline (backend lint + pytest + Alembic migrations against live PostgreSQL; frontend lint + Next.js build) running on every push and pull request.
- Immutable Docker image tagging via `GIT_SHA` for `backend`, `worker`, and `frontend` services; `make build`, `make deploy`, and `make rollback` targets in `Makefile`.
- OCI Vault secret provider abstraction; production deployments require `OCI_VAULT_ID` and fail fast at startup without it.
- Prompt evaluation script (`scripts/test_prompts.py`) with 13 deterministic acceptance criteria for `executive_summary` output quality.
- Explicit JSON schema, few-shot example, and `PROMPT_VERSION` tracking for AI executive summary prompts.
- Demo seed data script (`scripts/seed_demo_data.py`) for local AI context testing; idempotent across runs.

### Changed
- Credential encryption at rest using Fernet (AES-128-CBC + HMAC-SHA256); all cloud account secrets encrypted before insert/update and decrypted only at point of use.
- AWS IAM role separation: `role_arn` for read-only collectors, `remediation_role_arn` for Terraform apply — no silent fallback between roles.
- Claude model default updated to `claude-sonnet-4-6`; AI defaults raised to `AI_MAX_TOKENS=4000` and `AI_REQUEST_TIMEOUT_SECONDS=90`.
- Celery worker Docker healthcheck added using `celery inspect ping`.
- CORS request headers restricted from wildcard `*` to explicit allowlist (`Authorization`, `Content-Type`, `X-Tenant-ID`, `X-Request-ID`, `Accept`).
- Production startup blocks when `BACKEND_CORS_ORIGINS` contains `localhost`.
- `ClaudeProvider` sends a JSON-only system message on every call to enforce structured output.
- AI output validator extended to accept a controlled vocabulary of limitation signals (`LIMITATION_SIGNALS`) rather than a single rigid keyword match.
- Traceable AWS `RoleSessionName` pattern (`nb-{actor}-{operation}`) for CloudTrail attribution; hardcoded session names eliminated.
- Alembic configuration consolidated to `backend/alembic.ini` as sole source of truth; root `alembic.ini` removed.
- Terraform template catalog consolidated to `backend/terraform-catalog/`; root duplicate removed.

### Security
- Baseline `Content-Security-Policy` header added via `SecurityHeadersMiddleware` using `setdefault` to avoid downgrading upstream policies.
- Cloud Shell disabled by default behind `CLOUD_SHELL_ENABLED=false` feature flag; guard fires before authentication.
- `AI_PROVIDER=none` enforced as safe startup default; AI activation requires explicit environment configuration.
- Production secret provider blocks startup if no cloud vault is configured — no silent fallback to `.env`.

---

## [0.1.0] — Phase 0 Foundation

### Added
- Multi-tenant cloud governance foundation: tenant isolation, JWT authentication, API key management, role-based access, and structured audit logging.
- AWS cloud inventory: EC2, S3, RDS, VPC, IAM, and Lambda resource collection via assumed IAM roles with configurable session names.
- OCI cloud inventory: compute instances, VCNs, and object storage collection via API key authentication.
- Resource normalization engine: unified cross-provider schema enabling consistent findings and scoring across AWS and OCI.
- Findings engine: five governance dimensions — FinOps cost exposure, governance compliance, observability readiness, HA/DR readiness, and security posture.
- Risk scoring engine: deterministic composite scores per cloud account and per dimension, derived from live inventory data.
- AI analysis layer: provider abstraction supporting Claude (Anthropic), OpenAI, and DeepSeek; produces executive summaries and technical assessments from structured finding context.
- Reporting engine: AI-generated reports with per-finding remediation context, severity classifications, and downloadable outputs.
- Admin client cost optimization: idle compute detection, unattached volume identification, and tag-compliance findings with estimated savings.
- Cloud Shell controlled execution surface: `nb` command allowlist, Terraform validate/plan support, `apply` disabled, `destroy` blocked, full audit trail per command.
- Provisioning pipeline: Terraform validate/plan, Checkov policy gate integration, Infracost cost estimation, human approval workflow, controlled Terraform apply, and post-remediation validation.
- SaaS hardening baseline: per-endpoint rate limiting, request body size caps, `X-Frame-Options`, `X-Content-Type-Options`, and tenant-isolation middleware.
- Executive dashboard (Next.js + TailwindCSS): real-time operational scores, per-client inventory summary, risk breakdown, and one-click AI report viewer.
- FinOps analysis view with prioritized cost recommendations and monthly savings estimates.
- Multi-tenant client administration: per-tenant score, account count, resource count, and finding count.
- Docker Compose development stack: `backend` (FastAPI), `worker` (Celery), `frontend` (Next.js), `postgres`, `redis`, `prometheus`, `otel-collector`, `grafana`.
- Internal observability: Prometheus metrics for collectors, task queue, and finding counts; OpenTelemetry distributed tracing; structured JSON logging; Grafana dashboards.
- PostgreSQL schema managed through 16 Alembic migrations covering all domain models from auth through post-remediation validation.

### Security
- Baseline security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`) on all API responses.
- CORS policy with explicit origin allowlist; configurable per environment.
- Password minimum length enforcement and bcrypt hashing.
- Rate limiting on login, AI, reporting, and inventory scan endpoints.

### Documentation
- Architecture documentation for all major platform components (findings engine, scoring engine, AI analysis, resource normalization, reporting, observability, admin client, executive dashboard).
- API reference, quickstart guide, and contributing guide.
- Architecture Decision Records (ADR-001 through ADR-020) documenting every significant design choice.
- Risk register (RISK-001 through RISK-017) tracking active, mitigated, and accepted risks.
- Project state log (`planning/STATE.md`) with per-sprint delivery records and test suite baselines.
