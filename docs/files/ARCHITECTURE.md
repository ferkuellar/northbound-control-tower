# Architecture — Northbound Control Tower

> Component design, data model, and technical decisions for Phase 0.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Breakdown](#3-component-breakdown)
4. [Data Architecture](#4-data-architecture)
5. [Backend Structure](#5-backend-structure)
6. [Frontend Structure](#6-frontend-structure)
7. [Observability Design](#7-observability-design)
8. [Security Design](#8-security-design)
9. [Known Limitations](#9-known-limitations)
10. [Phase 1 Outlook](#10-phase-1-outlook)

---

## 1. Design Philosophy

### Modular Monolith First

Control Tower Phase 0 is a **modular monolith**: a single deployable unit with well-defined internal module boundaries. This is a deliberate choice, not a compromise.

The decision follows a principle of *operability before scalability*. Before splitting a system into services, the domain model must be stable, the team must understand the natural seams in the data, and operational complexity must be justified by actual load or organizational need. None of those conditions are met at Phase 0.

The monolith is structured so that the seams between modules are clean enough to extract into services later without rewriting. Each module has:
- A single responsibility
- No circular imports with other modules
- Public interfaces through its own `__init__.py` or `schemas.py`
- Its own domain models and logic

### What Phase 0 Explicitly Avoids

The following are architectural decisions to **not** implement yet:

| Deferred | Reason |
|---|---|
| Kubernetes | Adds operational surface area before the product is validated |
| Event buses (Kafka, SQS, SNS) | Current data volume is well within synchronous + polling range |
| Microservices | Domain boundaries are not stable enough to commit to service contracts |
| Auto-remediation | Requires trust in the scoring engine that is not yet established |
| Multi-cloud real-time streaming | Polling on a 2–5 minute cadence is sufficient and simpler |
| Advanced RBAC | Three roles (Admin, Analyst, Viewer) cover the current use case |
| Billing line-item ingestion | Aggregate FinOps diagnostics provide sufficient signal at Phase 0 |

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Cloud Accounts                          │
│               AWS (IAM Role) │ OCI (API Key)                 │
└──────────────┬───────────────────────────┬───────────────────┘
               │                           │
   ┌───────────▼───────────────────────────▼──────────┐
   │              Inventory Collectors                 │
   │     Scheduled Celery tasks per provider           │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │          Resource Normalization Layer             │
   │    Provider-specific → unified resource model     │
   │             (PostgreSQL + SQLAlchemy)             │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │               Findings Engine                    │
   │  Rule-based: idle compute · public exposure ·    │
   │  missing tags · unattached volumes · obs gaps    │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │             Risk Scoring Module                  │
   │      Severity × Impact × Coverage = Score        │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │             AI Context Builder                   │
   │   Structures findings into prompts for LLMs      │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │        Claude / OpenAI / DeepSeek                │
   │   Executive summaries · Technical assessments    │
   └──────────────┬────────────────────────────────────┘
                  │
   ┌──────────────▼──────────────────────┐
   │   Next.js Dashboard · PDF Reports  │
   │   Multi-tenant · Role-based RBAC   │
   └─────────────────────────────────────┘
```

See also: [`docs/northbound-architecture_1.png`](./northbound-architecture_1.png) — full diagram with supporting infrastructure.

---

## 3. Component Breakdown

### 3.1 Inventory Collectors

**Location:** `backend/collectors/`

**Responsibility:** Connect to cloud provider APIs, fetch raw resource data, and return normalized `NormalizedResource` objects.

**Design pattern:** Abstract Base Class (`InventoryCollector` in `collectors/base.py`). Each provider implements `collect() -> list[NormalizedResource]`. Adding a new provider means creating a new directory under `collectors/` and implementing the interface — the rest of the pipeline is unchanged.

**AWS collector** (`collectors/aws/`) collects:
- EC2 instances (compute)
- EBS volumes (block storage)
- S3 buckets (object storage)
- RDS instances (database)
- IAM users, roles, policies (identity)
- VPCs, subnets, security groups (network)
- CloudWatch alarms (observability)

**OCI collector** (`collectors/oci/`) collects:
- Compute instances
- Block volumes
- VCNs, subnets, security lists, NSGs (network)
- Load balancers
- Compartments, IAM users, groups, policies (identity)
- Monitoring alarms

**Error handling:** Each service call is wrapped in `_safe_collect()`. A failure in one service (e.g., access denied to CloudWatch) is recorded as a `partial_error` and collection continues for other services. The scan result reflects which services had errors without failing the entire collection.

**Scheduling:** Collectors run as Celery tasks, triggered per cloud account. The frequency is configurable via `AWS_SCAN_TIMEOUT_SECONDS` and `OCI_SCAN_TIMEOUT_SECONDS`.

---

### 3.2 Resource Normalization Layer

**Location:** `backend/collectors/normalization.py`, `collectors/aws/normalizers.py`, `collectors/oci/normalizers.py`

**Responsibility:** Transform raw provider-specific resource data into the unified `Resource` model stored in PostgreSQL.

**Key fields in the normalized model:**

| Field | Description |
|---|---|
| `provider` | `aws` or `oci` |
| `resource_type` | Normalized type: `compute`, `block_storage`, `database`, `network`, `identity`, `observability` |
| `resource_id` | Provider-native ID (e.g., `i-0abc123`, `ocid1.instance...`) |
| `raw_type` | Original resource type string (e.g., `AWS::EC2::Instance`) |
| `region` | Cloud region |
| `exposure_level` | `public`, `private`, or `unknown` |
| `lifecycle_status` | `running`, `stopped`, `available`, `detached`, etc. |
| `environment` | Extracted from tags: `prod`, `staging`, `dev` |
| `owner`, `cost_center`, `application` | Governance tags |
| `metadata_json` | Provider-specific fields that don't map to standard columns |
| `tags` | Raw tag key-value pairs |

**Fingerprinting:** Each resource is fingerprinted using a SHA-256 hash of `(tenant_id, cloud_account_id, provider, resource_id)`. This enables idempotent upserts — re-running a collection updates existing resources rather than creating duplicates.

---

### 3.3 Findings Engine

**Location:** `backend/findings/`

**Responsibility:** Evaluate every resource against a set of rules and produce findings (potential issues) with severity, evidence, and remediation recommendations.

**Architecture:** The engine uses a **Registry pattern**. `FindingRuleRegistry` holds all registered rules. `FindingsEngine.run()` loads all resources for a tenant/account and evaluates every resource against every rule. Rules are independent — a resource can trigger multiple findings.

**Built-in rules (Phase 0):**

| Rule | Finding Type | Category | Default Severity |
|---|---|---|---|
| `MissingTagsRule` | `missing_tags` | Governance | Medium |
| `PublicExposureRule` | `public_exposure` | Security | High |
| `IdleComputeRule` | `idle_compute` | FinOps | Medium |
| `UnattachedVolumeRule` | `unattached_volume` | FinOps | Low |
| `ObservabilityGapRule` | `observability_gap` | Observability | Medium |

**Finding fingerprint:** Each finding is identified by a SHA-256 hash of `(tenant_id, cloud_account_id, provider, resource_id, finding_type, rule_id)`. This makes finding upserts idempotent and allows tracking when a finding first appeared vs. when it was last seen.

**Evidence sanitization:** Before persisting, `_safe_evidence()` strips keys that could contain credentials (`secret`, `private_key`, `token`, `password`, `key_content`). Evidence is safe to store in plaintext.

**Adding a new rule:** See [CONTRIBUTING.md](./CONTRIBUTING.md#how-to-add-a-new-finding-type).

---

### 3.4 Risk Scoring Module

**Location:** `backend/` (scoring logic referenced in `api/routes/scores.py` and related services)

**Responsibility:** Aggregate findings into dimensional scores (0–100) per cloud account.

**Dimensions:**

| Dimension | Driven by |
|---|---|
| FinOps | `idle_compute`, `unattached_volume` findings |
| Governance | `missing_tags` findings |
| Observability | `observability_gap` findings |
| Security | `public_exposure` findings |
| Resilience | HA/DR-related findings |
| Overall | Composite of all dimensions |

**Scoring model:** `Severity × Impact × Coverage = Score`. Higher severity findings with broader coverage lower the score more. A score of 100 means no active findings in that dimension. The scoring is **deterministic** — the same set of findings always produces the same scores.

**Score labels:**

| Range | Label |
|---|---|
| 90–100 | Excellent |
| 75–89 | Good |
| 60–74 | Fair |
| 0–59 | Poor |

---

### 3.5 AI Context Builder

**Location:** `backend/ai/context_builder.py`

**Responsibility:** Transform normalized findings and scores into a structured JSON context that is passed as input to LLM prompts.

The context builder:
- Loads findings filtered by tenant/account/provider
- Loads latest scores for each dimension
- Loads resource inventory summary
- Applies limits (`AI_MAX_INPUT_FINDINGS`, `AI_MAX_INPUT_RESOURCES`) to stay within token budgets
- Structures everything into a prompt-ready dict

The context is versioned (`PROMPT_VERSION` in `ai/prompts.py`) so that changes to the prompt structure are tracked and correlated with output quality over time.

---

### 3.6 AI Analysis Layer

**Location:** `backend/ai/`

**Responsibility:** Send the structured context to an LLM provider and validate the output.

**Design pattern:** Strategy. `BaseAIProvider` (ABC in `ai/providers/base.py`) defines the interface:
```python
def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str
def health_check(self) -> AIProviderStatus
```

Implementations: `ClaudeProvider`, `OpenAIProvider`, `DeepSeekProvider`. Switching providers requires only changing `AI_PROVIDER` in the environment — no code changes.

**Analysis types:**
- `executive_summary` — plain-language narrative for C-level audiences
- `technical_assessment` — detailed findings, severity, and remediation steps

**Observability:** Every analysis request is tracked with Prometheus counters (`AI_ANALYSIS_REQUESTS_TOTAL`, `AI_ANALYSIS_FAILURES_TOTAL`) and histograms (`AI_ANALYSIS_DURATION_SECONDS`), labeled by provider and analysis type. Every analysis is also written to an audit log.

---

### 3.7 Report & Dashboard Layer

**Location:** `frontend/`, `backend/api/routes/reports.py`

**Responsibility:** Surface all data to users through the Next.js dashboard and generate downloadable PDF reports.

**Dashboard sections:**
- Executive Dashboard: scores, findings summary, inventory summary, risk summary
- Inventory: full resource table with filtering
- Findings: finding table with severity/status/type filters
- Scores: score cards with history charts
- Risks: risk breakdown by type
- Trends: score history over time

**Report output:** PDF export of executive or technical assessments, generated server-side and downloadable directly from the dashboard.

---

## 4. Data Architecture

### 4.1 Core Models

**`tenants`** — top-level isolation unit. Every other model is scoped to a tenant.

```
id (UUID PK)
name (string)
slug (string, unique)
is_active (bool)
```

**`users`** — platform users with role-based access.

```
id (UUID PK)
tenant_id (UUID FK → tenants)
email (string, unique within tenant)
hashed_password (string — bcrypt)
full_name (string)
role (enum: ADMIN | ANALYST | VIEWER)
is_active (bool)
```

**`cloud_accounts`** — registered cloud provider accounts.

```
id (UUID PK)
tenant_id (UUID FK → tenants)
provider (enum: aws | oci)
name (string)
account_id (string, nullable)
auth_type (enum: access_keys | role_arn | oci_api_key | oci_config | profile)
access_key_id (string, nullable)           -- ⚠ Phase 0: plaintext, Phase 1: encrypted
secret_access_key (string, nullable)       -- ⚠ Phase 0: plaintext, Phase 1: encrypted
role_arn (string, nullable)
external_id (string, nullable)
tenancy_ocid (string, nullable)
user_ocid (string, nullable)
fingerprint (string, nullable)
private_key (string, nullable)             -- ⚠ Phase 0: plaintext, Phase 1: encrypted
private_key_passphrase (string, nullable)  -- ⚠ Phase 0: plaintext, Phase 1: encrypted
default_region (string)
is_active (bool)
```

> **Security note:** Credential columns are stored in plaintext in Phase 0. This is acknowledged technical debt. Phase 1 will encrypt them with `pgcrypto` or migrate to AWS Secrets Manager / OCI Vault. See [PLAN_MEJORA.md](../PLAN_MEJORA_northbound_control_tower.md) — Fase A, tarea F01.

**`resources`** — normalized cloud resources from all providers.

```
id (UUID PK)
tenant_id (UUID FK → tenants)
cloud_account_id (UUID FK → cloud_accounts)
provider (string)
resource_type (string)        -- compute, block_storage, database, network, identity, observability
resource_id (string)          -- provider-native ID
raw_type (string)             -- original provider type string
fingerprint (string, unique)  -- SHA-256 for upsert idempotency
name (string, nullable)
region (string)
exposure_level (string)       -- public | private | unknown
lifecycle_status (string)     -- running | stopped | available | detached | etc.
environment (string)          -- prod | staging | dev | unknown
owner, cost_center, application, service_name (string, nullable)
tags (JSONB)
metadata_json (JSONB)
relationships (JSONB)
discovered_at (timestamp)
```

**`findings`** — rule evaluation results.

```
id (UUID PK)
tenant_id (UUID FK → tenants)
cloud_account_id (UUID FK → cloud_accounts)
resource_id (UUID FK → resources, nullable)
provider (string)
finding_type (string)         -- missing_tags | public_exposure | idle_compute | etc.
category (string)             -- finops | governance | security | observability | resilience
severity (string)             -- critical | high | medium | low | informational
status (string)               -- open | acknowledged | resolved | false_positive
rule_id (string)              -- identifies which rule produced the finding
fingerprint (string, unique)  -- SHA-256 for upsert idempotency
title (string)
description (text)
evidence (JSONB)              -- sanitized, no credentials
recommendation (text)
estimated_monthly_waste (decimal, nullable)
first_seen_at (timestamp)
last_seen_at (timestamp)
```

**`ai_analyses`** — persisted AI analysis records.

```
id (UUID PK)
tenant_id (UUID FK → tenants)
cloud_account_id (UUID FK, nullable)
ai_provider (string)          -- claude | openai | deepseek
analysis_type (string)        -- executive_summary | technical_assessment
status (string)               -- pending | completed | failed
model_name (string)
prompt_version (string)
input_summary (JSONB)
output (JSONB)
raw_text (text)
error_message (text, nullable)
created_by_user_id (UUID FK → users)
completed_at (timestamp, nullable)
```

### 4.2 Migration Strategy

Migrations are managed with Alembic. Migration files live in `backend/alembic/versions/` and are named with a timestamp prefix and sequential number for clarity:

```
2026_05_11_0125-0001_auth_tenant_audit_base.py
2026_05_11_0145-0002_aws_inventory_base.py
2026_05_11_0215-0003_oci_cloud_account_fields.py
2026_05_11_0300-0004_resource_normalization_engine.py
2026_05_11_0330-0005_findings_engine.py
2026_05_11_0400-0006_risk_scoring_engine.py
2026_05_11_0430-0007_ai_analysis_layer.py
2026_05_13_0100-0008_reporting_engine.py
2026_05_13_0200-0009_saas_hardening_audit.py
```

Run migrations with:
```bash
docker compose run --rm backend alembic upgrade head
```

---

## 5. Backend Structure

```
backend/
├── api/
│   ├── main.py              # FastAPI app factory, middleware registration
│   ├── router.py            # API router with /api/v1 prefix
│   └── routes/
│       ├── auth.py          # Login, /me, token refresh
│       ├── tenants.py       # Tenant management
│       ├── cloud_accounts.py # Account CRUD, credential validation
│       ├── inventory.py     # Trigger scans, scan status
│       ├── resources.py     # Resource listing and detail
│       ├── findings.py      # Finding listing, status updates, summary
│       ├── scores.py        # Latest scores, score history, summary
│       ├── ai.py            # Trigger analysis, list analyses, context preview
│       ├── reports.py       # Report generation, listing, download
│       ├── audit.py         # Audit log listing
│       ├── platform.py      # Platform-level stats
│       ├── health.py        # /health/live, /health/ready
│       └── status.py        # API version, provider status
├── collectors/
│   ├── base.py              # InventoryCollector ABC
│   ├── normalization.py     # NormalizedResource dataclass
│   ├── aws/
│   │   ├── collector.py     # AWSInventoryCollector
│   │   ├── normalizers.py   # Per-resource normalization functions
│   │   └── session.py       # AWSSessionFactory (IAM role / access key)
│   └── oci/
│       ├── collector.py     # OCIInventoryCollector
│       ├── normalizers.py
│       ├── session.py       # OCISessionFactory
│       └── errors.py        # OCI-specific error handling
├── findings/
│   ├── engine.py            # FindingsEngine (orchestrates rules against resources)
│   ├── rules.py             # BaseFindingRule + 5 built-in rule implementations
│   ├── registry.py          # FindingRuleRegistry (auto-discovers rules)
│   ├── enums.py             # FindingType, FindingCategory, FindingSeverity
│   └── schemas.py           # FindingCandidate dataclass
├── ai/
│   ├── service.py           # AIAnalysisService (orchestrates analysis lifecycle)
│   ├── context_builder.py   # AIContextBuilder (findings → prompt context)
│   ├── prompts.py           # Prompt templates and versioning
│   ├── validators.py        # Output validation
│   ├── provider.py          # Provider factory (get_ai_provider)
│   ├── providers/
│   │   ├── base.py          # BaseAIProvider ABC
│   │   ├── claude.py        # Anthropic Claude implementation
│   │   ├── openai_provider.py # OpenAI implementation
│   │   └── deepseek.py      # DeepSeek implementation
│   ├── schemas.py           # Request/response schemas
│   ├── enums.py             # AIProvider, AIAnalysisStatus, AIAnalysisType
│   └── errors.py            # AIAnalysisError, AIProviderConfigurationError
├── auth/
│   ├── security.py          # JWT encode/decode, bcrypt hash/verify
│   ├── dependencies.py      # FastAPI deps: get_current_user, require_roles
│   ├── guards.py            # Route-level auth guards
│   ├── permissions.py       # Permission definitions
│   ├── roles.py             # Role hierarchy
│   └── schemas.py           # Auth request/response schemas
├── core/
│   ├── config.py            # Settings (pydantic-settings, env-driven)
│   ├── database.py          # SQLAlchemy engine, session, Base, TimestampMixin
│   ├── errors.py            # Exception handlers, standard error responses
│   ├── logging.py           # Structured JSON logging configuration
│   └── redis.py             # Redis client factory
├── middleware/
│   ├── rate_limit.py        # RateLimitMiddleware (per-route, per-user/IP)
│   └── tenant.py            # TenantContextMiddleware (JWT → request.state.tenant_id)
├── models/                  # SQLAlchemy ORM models (one file per table)
├── security/
│   ├── headers.py           # SecurityHeadersMiddleware, RequestValidationMiddleware
│   ├── rate_limit.py        # InMemoryRateLimiter (Phase 0; Redis in Phase 1)
│   ├── secrets.py           # Secret provider abstraction
│   └── validation.py        # Input sanitization utilities
├── services/
│   ├── inventory.py         # Inventory collection orchestration
│   ├── audit_log.py         # Audit log write helper
│   └── platform_scope.py   # Platform-level aggregation queries
├── workers/
│   └── celery_app.py        # Celery app, task signals, OTel instrumentation
├── observability/
│   ├── metrics.py           # Prometheus metric definitions
│   ├── tracing.py           # OpenTelemetry configuration
│   ├── middleware.py        # PrometheusHTTPMetricsMiddleware, RequestIdMiddleware
│   └── instruments.py      # operation_span() context manager
└── alembic/
    ├── env.py
    └── versions/            # Migration files
```

### Middleware Stack (execution order)

Middlewares are applied in reverse registration order in Starlette/FastAPI. As registered in `api/main.py`:

```
Request →
  CORS
  SecurityHeadersMiddleware      (X-Frame-Options, X-Content-Type-Options, etc.)
  RequestValidationMiddleware    (Content-Length, Content-Type validation)
  RateLimitMiddleware            (per-route, per-user/IP)
  TenantContextMiddleware        (JWT → tenant_id in request.state)
  PrometheusHTTPMetricsMiddleware (request duration, status code counters)
  RequestIdMiddleware            (X-Request-ID header injection)
→ Route handler
```

---

## 6. Frontend Structure

```
frontend/
├── app/
│   ├── layout.tsx           # Root layout, font loading
│   ├── page.tsx             # Root redirect → /dashboard or /login
│   ├── dashboard/
│   │   └── page.tsx         # Executive Dashboard page shell
│   ├── login/
│   │   └── page.tsx         # Login page
│   └── error.tsx            # Global error boundary
├── components/
│   ├── dashboard/
│   │   ├── ExecutiveDashboard.tsx  # Main dashboard client component
│   │   ├── MetricCard.tsx
│   │   └── ChartPanel.tsx
│   ├── findings/
│   │   └── FindingsTable.tsx
│   ├── resources/
│   │   └── InventoryTable.tsx
│   ├── scores/
│   │   ├── ScoreCards.tsx
│   │   └── ScoreCharts.tsx
│   ├── layout/
│   │   └── DashboardShell.tsx     # Sidebar + topbar shell
│   └── ui/                        # Badge, Button, Card, EmptyState, Input, Select
├── lib/
│   ├── api.ts               # apiFetch wrapper, all API call functions
│   ├── auth.ts              # getToken, setStoredUser, clearSession
│   ├── types.ts             # Full TypeScript type definitions
│   └── formatters.ts        # countBy, openFindings, labelize, etc.
└── types/
    └── lucide-react.d.ts    # Icon type augmentation
```

**Tech stack:** Next.js 16 (App Router) · TailwindCSS 3 · Apache ECharts 5 · Lucide React · TypeScript 5.7.

**Authentication flow:** Token stored client-side (via `lib/auth.ts`). All API calls include `Authorization: Bearer <token>`. A 401 response clears the session and redirects to `/login`.

---

## 7. Observability Design

### Prometheus Metrics

Custom metrics defined in `observability/metrics.py`:

| Metric | Type | Labels |
|---|---|---|
| `http_requests_total` | Counter | method, path, status_code |
| `http_request_duration_seconds` | Histogram | method, path |
| `celery_tasks_total` | Counter | task_name, status |
| `celery_task_duration_seconds` | Histogram | task_name, status |
| `ai_analysis_requests_total` | Counter | provider, analysis_type, status |
| `ai_analysis_duration_seconds` | Histogram | provider, analysis_type, status |
| `ai_analysis_failures_total` | Counter | provider, analysis_type |

Prometheus scrapes `/metrics` on the backend. The endpoint is protected behind `PROMETHEUS_METRICS_ENABLED=true`.

### OpenTelemetry

Tracing is configured in `observability/tracing.py`. The `operation_span()` context manager in `observability/instruments.py` wraps critical operations (AI analysis, inventory collection) with spans exported to the OTEL Collector via gRPC on port 4317.

```python
with operation_span("ai.analysis", provider="claude", operation_name="ai_analysis"):
    result = provider.generate_analysis(prompt, max_tokens, temperature)
```

### Grafana

Pre-provisioned dashboards in `observability/grafana/dashboards/`. The `northbound-platform-overview.json` dashboard covers API request rates, Celery task throughput, AI analysis performance, and error rates.

---

## 8. Security Design

### Authentication

JWT tokens (HS256) issued on login with configurable expiry (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, default 60). Tokens carry `sub` (user ID) and `tenant_id` claims.

Password hashing: bcrypt via passlib with automatic cost factor management.

### Authorization

Three roles enforced at route level via `require_roles()` dependency:

| Role | Permissions |
|---|---|
| `ADMIN` | Full access including tenant management and cloud account CRUD |
| `ANALYST` | Read/write on inventory, findings, AI analysis, reports |
| `VIEWER` | Read-only on all operational data |

### Tenant Isolation

`TenantContextMiddleware` extracts `tenant_id` from the JWT and sets it on `request.state`. All database queries in route handlers filter by `tenant_id`. A mismatch between the token's `tenant_id` and the `X-Tenant-ID` header returns 403.

### Rate Limiting

Routes subject to rate limiting (Phase 0 — in-memory, per-process):

| Route | Limit | Key |
|---|---|---|
| `POST /api/v1/auth/login` | 5/min | IP address |
| `POST /api/v1/ai/analyze` | 10/min | User ID |
| `POST /api/v1/reports/generate` | 5/min | User ID |
| `POST /api/v1/inventory/*/scan/*` | 5/min | Tenant ID |

> **Known limitation:** The current `InMemoryRateLimiter` is not distributed. Phase 1 will replace it with a Redis sliding window implementation. See [PLAN_MEJORA.md](../PLAN_MEJORA_northbound_control_tower.md).

### Security Headers

Applied by `SecurityHeadersMiddleware` to every response:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Referrer-Policy: no-referrer
Permissions-Policy: camera=(), microphone=(), geolocation=()
Strict-Transport-Security: max-age=31536000; includeSubDomains  (HTTPS only)
```

---

## 9. Known Limitations

| Limitation | Impact | Phase target |
|---|---|---|
| Cloud credentials stored in plaintext (PostgreSQL) | DB compromise exposes all credentials | Phase 1 |
| Rate limiter is in-memory (not distributed) | Ineffective with multiple API replicas | Phase 1 |
| No Content-Security-Policy header | XSS not mitigated at HTTP layer | Phase 1 |
| Dashboard loads 8 endpoints in parallel with no partial fallback | One slow endpoint fails entire dashboard | Phase 1 |
| No frontend test framework | Zero test coverage on UI components | Phase 1 |
| Collector tests absent | AWS/OCI collectors not covered by unit tests | Phase 1 |

---

## 10. Phase 1 Outlook

Phase 1 is planned to address the security-critical items from Phase 0 and expand cloud coverage:

- **Azure support** — new `collectors/azure/` module implementing `InventoryCollector`
- **Credential encryption** — `pgcrypto` column-level encryption or migration to Secrets Manager
- **Distributed rate limiting** — Redis sliding window replacing `InMemoryRateLimiter`
- **Frontend testing** — vitest + @testing-library/react
- **Collector unit tests** — boto3 mock suite for AWS, oci mock for OCI
- **Repository pattern** — `FindingRepository`, `ResourceRepository` to decouple services from ORM
- **Advanced RBAC** — per-resource permissions beyond the three current roles
- **Billing ingestion** — AWS Cost Explorer and OCI Cost Analysis integration for line-item FinOps
