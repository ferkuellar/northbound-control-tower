# API Reference — Northbound Control Tower

> Full endpoint reference for the Northbound Control Tower REST API.

Interactive documentation is also available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc) when running locally.

---

## Base URL

```
http://localhost:8000/api/v1       # local development
https://your-domain.com/api/v1    # production
```

All endpoints are prefixed with `/api/v1` except health checks (`/health/*`) and metrics (`/metrics`).

---

## Authentication

All endpoints except `/api/v1/auth/login` and `/health/*` require a Bearer token.

```
Authorization: Bearer <access_token>
```

Tokens are obtained from `POST /api/v1/auth/login` and expire after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes).

---

## Error Format

All errors return a consistent JSON structure:

```json
{
  "detail": "Human-readable error message"
}
```

**Common status codes:**

| Code | Meaning |
|---|---|
| `400` | Bad request — invalid input |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — insufficient role or tenant mismatch |
| `404` | Resource not found |
| `409` | Conflict — duplicate resource |
| `413` | Request body too large (> 1 MB) |
| `415` | Unsupported media type |
| `422` | Validation error — request body schema violation |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

---

## Rate Limits

| Endpoint | Limit | Window | Key |
|---|---|---|---|
| `POST /auth/login` | 5 requests | 60 seconds | IP address |
| `POST /ai/analyze` | 10 requests | 60 seconds | User ID |
| `POST /reports/generate` | 5 requests | 60 seconds | User ID |
| `POST /inventory/*/scan/*` | 5 requests | 60 seconds | Tenant ID |

Rate-limited responses include `Retry-After: <seconds>` in the response header.

---

## Endpoints

### Auth

#### `POST /auth/login`

Authenticate and obtain a JWT access token.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "your-password"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

#### `GET /auth/me`

Return the authenticated user's profile.

**Response `200`:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "full_name": "Admin User",
  "role": "ADMIN"
}
```

---

### Tenants

#### `POST /tenants`

Create a new tenant. **No auth required** on a fresh installation; may require ADMIN role depending on configuration.

**Request:**
```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "industry": "Technology",
  "contact_name": "Jane Smith",
  "contact_email": "jane@acme.com"
}
```

**Response `201`:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "is_active": true,
  "created_at": "2026-05-14T00:00:00Z"
}
```

---

#### `GET /tenants`

List all tenants. **ADMIN only.**

**Response `200`:** Array of tenant objects.

---

#### `GET /tenants/{tenant_id}`

Get a single tenant by ID. **ADMIN only.**

---

#### `POST /tenants/{tenant_id}/users`

Create a user within a tenant. **ADMIN only.**

**Request:**
```json
{
  "email": "analyst@acme.com",
  "password": "SecurePassword123!",
  "full_name": "Jane Analyst",
  "role": "ANALYST"
}
```

**Response `201`:** User object (password not returned).

---

### Cloud Accounts

#### `POST /cloud-accounts`

Register a cloud provider account. **ADMIN only.**

**Request — AWS Access Keys:**
```json
{
  "provider": "aws",
  "name": "AWS Production",
  "auth_type": "access_keys",
  "access_key_id": "AKIAIOSFODNN7EXAMPLE",
  "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "default_region": "us-east-1"
}
```

**Request — AWS IAM Role:**
```json
{
  "provider": "aws",
  "name": "AWS Production",
  "auth_type": "role_arn",
  "role_arn": "arn:aws:iam::123456789012:role/NorthboundReadOnly",
  "external_id": "optional-external-id",
  "default_region": "us-east-1"
}
```

**Request — OCI API Key:**
```json
{
  "provider": "oci",
  "name": "OCI Production",
  "auth_type": "oci_api_key",
  "tenancy_ocid": "ocid1.tenancy.oc1..aaaa...",
  "user_ocid": "ocid1.user.oc1..aaaa...",
  "fingerprint": "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
  "default_region": "us-ashburn-1"
}
```

**Response `201`:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
  "provider": "aws",
  "name": "AWS Production",
  "auth_type": "access_keys",
  "default_region": "us-east-1",
  "is_active": true,
  "created_at": "2026-05-14T00:00:00Z"
}
```

> Credentials are never returned in responses.

---

#### `GET /cloud-accounts`

List all cloud accounts for the authenticated tenant.

**Response `200`:** Array of cloud account objects (no credentials).

---

#### `GET /cloud-accounts/{account_id}`

Get a single cloud account.

---

#### `PATCH /cloud-accounts/{account_id}`

Update a cloud account (name, region, active status). **ADMIN only.**

---

#### `DELETE /cloud-accounts/{account_id}`

Deactivate a cloud account. **ADMIN only.** Does not delete historical data.

---

### Inventory

#### `POST /inventory/accounts/{account_id}/scan`

Trigger an inventory collection scan for a cloud account. Returns a Celery task ID.

**Response `202`:**
```json
{
  "task_id": "abc123de-f456-7890-abcd-ef1234567890",
  "account_id": "770e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "queued_at": "2026-05-14T00:00:00Z"
}
```

---

#### `GET /inventory/tasks/{task_id}`

Check the status of an inventory scan task.

**Response `200`:**
```json
{
  "task_id": "abc123de-f456-7890-abcd-ef1234567890",
  "status": "completed",
  "resources_collected": 47,
  "findings_created": 3,
  "findings_updated": 12,
  "partial_errors": [
    {
      "service": "cloudwatch_alarms",
      "type": "access_denied",
      "message": "User is not authorized to call DescribeAlarms"
    }
  ],
  "execution_time_ms": 42300,
  "completed_at": "2026-05-14T00:00:42Z"
}
```

**Task statuses:** `pending` | `running` | `completed` | `failed`

---

#### `GET /inventory/accounts/{account_id}/scans`

List historical scans for a cloud account.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 20 | Max results |
| `offset` | integer | 0 | Pagination offset |

---

### Resources

#### `GET /resources`

List normalized cloud resources for the authenticated tenant.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `cloud_account_id` | UUID | Filter by account |
| `provider` | string | `aws` or `oci` |
| `resource_type` | string | `compute`, `block_storage`, `database`, `network`, `identity`, `observability` |
| `region` | string | Cloud region |
| `exposure_level` | string | `public`, `private`, `unknown` |
| `environment` | string | `prod`, `staging`, `dev` |
| `limit` | integer | Default: 100, max: 500 |
| `offset` | integer | Default: 0 |

**Response `200`:**
```json
[
  {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
    "cloud_account_id": "770e8400-e29b-41d4-a716-446655440000",
    "provider": "aws",
    "resource_type": "compute",
    "resource_id": "i-0abc123def456",
    "raw_type": "AWS::EC2::Instance",
    "name": "prod-api-server-01",
    "region": "us-east-1",
    "availability_zone": "us-east-1a",
    "exposure_level": "private",
    "lifecycle_status": "running",
    "environment": "prod",
    "owner": "platform-team",
    "cost_center": "engineering",
    "application": "api-gateway",
    "tags": {"Name": "prod-api-server-01", "Env": "prod"},
    "metadata_json": {"instance_type": "t3.medium", "cpu_average_14d": 2.3},
    "discovered_at": "2026-05-14T00:00:00Z"
  }
]
```

---

#### `GET /resources/{resource_id}`

Get a single resource by ID.

---

### Findings

#### `GET /findings`

List findings for the authenticated tenant.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `cloud_account_id` | UUID | Filter by account |
| `provider` | string | `aws` or `oci` |
| `finding_type` | string | `missing_tags`, `public_exposure`, `idle_compute`, `unattached_volume`, `observability_gap` |
| `category` | string | `finops`, `governance`, `security`, `observability`, `resilience` |
| `severity` | string | `critical`, `high`, `medium`, `low`, `informational` |
| `status` | string | `open`, `acknowledged`, `resolved`, `false_positive` |
| `limit` | integer | Default: 100, max: 500 |
| `offset` | integer | Default: 0 |

**Response `200`:**
```json
[
  {
    "id": "990e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
    "cloud_account_id": "770e8400-e29b-41d4-a716-446655440000",
    "resource_id": "880e8400-e29b-41d4-a716-446655440000",
    "provider": "aws",
    "finding_type": "missing_tags",
    "category": "governance",
    "severity": "medium",
    "status": "open",
    "rule_id": "phase6.missing_tags.v1",
    "title": "Resource is missing required governance tags",
    "description": "Resource prod-api-server-01 is missing required tags: cost_center, application.",
    "evidence": {
      "provider": "aws",
      "resource_id": "i-0abc123def456",
      "missing_tags": ["cost_center", "application"],
      "region": "us-east-1"
    },
    "recommendation": "Add environment, owner, cost_center, and application tags through the standard tagging workflow.",
    "estimated_monthly_waste": null,
    "first_seen_at": "2026-05-10T00:00:00Z",
    "last_seen_at": "2026-05-14T00:00:00Z"
  }
]
```

---

#### `GET /findings/summary`

Get findings counts grouped by severity and type.

**Response `200`:**
```json
{
  "total": 15,
  "by_severity": {
    "critical": 0,
    "high": 2,
    "medium": 8,
    "low": 5
  },
  "by_type": {
    "missing_tags": 6,
    "public_exposure": 2,
    "idle_compute": 3,
    "unattached_volume": 2,
    "observability_gap": 2
  },
  "by_status": {
    "open": 10,
    "acknowledged": 3,
    "resolved": 2
  }
}
```

---

#### `GET /findings/{finding_id}`

Get a single finding by ID.

---

#### `PATCH /findings/{finding_id}/status`

Update a finding's status. **ANALYST or ADMIN.**

**Request:**
```json
{
  "status": "acknowledged",
  "note": "Accepted risk — reviewed by security team 2026-05-14"
}
```

**Response `200`:** Updated finding object.

---

### Scores

#### `GET /scores/latest`

Get the latest scores for the authenticated tenant across all dimensions and accounts.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `cloud_account_id` | UUID | Filter to a specific account |

**Response `200`:**
```json
{
  "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
  "computed_at": "2026-05-14T00:00:00Z",
  "overall": {
    "score": 73,
    "label": "Fair",
    "trend": "stable"
  },
  "dimensions": {
    "finops": {"score": 64, "label": "Fair", "trend": "stable", "top_driver": "idle_compute"},
    "governance": {"score": 68, "label": "Fair", "trend": "stable", "top_driver": "missing_tags"},
    "observability": {"score": 72, "label": "Fair", "trend": "stable", "top_driver": null},
    "security": {"score": 84, "label": "Good", "trend": "stable", "top_driver": null},
    "resilience": {"score": 78, "label": "Good", "trend": "stable", "top_driver": null}
  }
}
```

---

#### `GET /scores/summary`

Get a high-level score summary for dashboard display.

---

#### `GET /scores/history`

Get score history over time.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 100 | Max data points |
| `cloud_account_id` | UUID | — | Filter by account |
| `dimension` | string | — | Filter to one dimension |

**Response `200`:**
```json
[
  {
    "computed_at": "2026-05-14T00:00:00Z",
    "overall": 73,
    "finops": 64,
    "governance": 68,
    "observability": 72,
    "security": 84,
    "resilience": 78
  }
]
```

---

### AI Analysis

#### `POST /ai/analyze`

Trigger an AI analysis. **ANALYST or ADMIN.**

**Request:**
```json
{
  "analysis_type": "executive_summary",
  "provider": "claude",
  "cloud_account_id": "770e8400-e29b-41d4-a716-446655440000",
  "cloud_provider": "aws"
}
```

**`analysis_type`:** `executive_summary` | `technical_assessment`

**`provider`:** `claude` | `openai` | `deepseek` | `null` (uses `AI_PROVIDER` env var)

**Response `200`:**
```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "ai_provider": "claude",
  "analysis_type": "executive_summary",
  "model_name": "claude-3-5-sonnet-latest",
  "prompt_version": "v2",
  "output": {
    "executive_summary": "...",
    "risk_posture": "...",
    "top_findings": [...],
    "recommended_actions": [...]
  },
  "completed_at": "2026-05-14T00:00:15Z"
}
```

---

#### `GET /ai/analyses`

List AI analyses for the authenticated tenant.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `cloud_account_id` | UUID | Filter by account |
| `analysis_type` | string | Filter by type |
| `limit` | integer | Default: 20 |

---

#### `GET /ai/analyses/{analysis_id}`

Get a single AI analysis by ID.

---

#### `GET /ai/context-preview`

Preview the context that would be sent to the AI provider, without triggering an analysis. Useful for debugging and token estimation.

**Query parameters:** `cloud_account_id`, `cloud_provider`

**Response `200`:** The raw context dict that would be passed to the prompt builder.

---

#### `GET /ai/providers`

Get the status of all configured AI providers.

**Response `200`:**
```json
[
  {
    "provider": "claude",
    "configured": true,
    "enabled": true,
    "model_name": "claude-3-5-sonnet-latest",
    "message": "OK"
  },
  {
    "provider": "openai",
    "configured": false,
    "enabled": false,
    "model_name": "gpt-4o-mini",
    "message": "OPENAI_API_KEY not set"
  },
  {
    "provider": "deepseek",
    "configured": false,
    "enabled": false,
    "model_name": "deepseek-chat",
    "message": "DEEPSEEK_API_KEY not set"
  }
]
```

---

### Reports

#### `POST /reports/generate`

Generate a structured report combining scores, findings, and AI analysis. **ANALYST or ADMIN.**

**Request:**
```json
{
  "report_type": "executive",
  "cloud_account_id": "770e8400-e29b-41d4-a716-446655440000",
  "include_ai_summary": true,
  "ai_provider": "claude"
}
```

**`report_type`:** `executive` | `technical` | `finops`

**Response `202`:** Report object with `status: "pending"` and report `id`.

---

#### `GET /reports`

List reports for the authenticated tenant.

---

#### `GET /reports/{report_id}`

Get a single report by ID.

---

#### `GET /reports/{report_id}/download`

Download the report as PDF.

**Response:** `application/pdf` stream.

---

### Audit Log

#### `GET /audit`

Get the audit log for the authenticated tenant. **ADMIN only.**

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `user_id` | UUID | Filter by user |
| `action` | string | e.g., `ai_analysis_started`, `finding_status_updated` |
| `resource_type` | string | e.g., `ai_analysis`, `finding`, `cloud_account` |
| `limit` | integer | Default: 100 |
| `offset` | integer | Default: 0 |

**Response `200`:**
```json
[
  {
    "id": "bb0e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "ai_analysis_completed",
    "resource_type": "ai_analysis",
    "resource_id": "aa0e8400-e29b-41d4-a716-446655440000",
    "metadata": {
      "provider": "claude",
      "analysis_type": "executive_summary",
      "execution_time_ms": 14320
    },
    "created_at": "2026-05-14T00:00:15Z"
  }
]
```

---

### Platform

#### `GET /platform/stats`

Platform-level statistics (all tenants). **ADMIN only.**

**Response `200`:**
```json
{
  "total_tenants": 450,
  "active_tenants": 448,
  "total_cloud_accounts": 892,
  "total_resources": 41230,
  "total_findings": 8904,
  "open_findings": 6120,
  "analyses_last_30_days": 1240
}
```

---

### Health

#### `GET /health/live`

Liveness probe. Returns 200 if the process is running.

**Response `200`:**
```json
{"status": "ok"}
```

#### `GET /health/ready`

Readiness probe. Returns 200 only if the database and Redis are reachable.

**Response `200`:**
```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

**Response `503`** (when unhealthy):
```json
{
  "status": "error",
  "database": "error",
  "redis": "ok",
  "detail": "Database connection failed"
}
```

---

### Metrics

#### `GET /metrics`

Prometheus metrics endpoint. Returns metrics in Prometheus text format.

Only available when `PROMETHEUS_METRICS_ENABLED=true` (default).

---

## Async Operations

Inventory scans and report generation are asynchronous. They return immediately with a task/report ID and a `pending` status. Poll the corresponding `GET` endpoint to check progress.

**Typical completion times:**

| Operation | Typical duration |
|---|---|
| AWS inventory scan (50–200 resources) | 30–90 seconds |
| OCI inventory scan (50–100 resources) | 20–60 seconds |
| AI executive summary | 10–30 seconds |
| AI technical assessment | 15–45 seconds |
| PDF report generation | 5–15 seconds |

---

## Changelog

| Version | Date | Changes |
|---|---|---|
| v1 | 2026-05-11 | Initial release — auth, tenants, cloud accounts, inventory, findings, scores |
| v1.1 | 2026-05-13 | Added AI analysis, reports, audit log, platform stats |
