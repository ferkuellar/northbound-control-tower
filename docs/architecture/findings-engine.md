# Findings Engine

## Purpose

The Findings Engine evaluates normalized AWS and OCI resources with deterministic rules and persists actionable records for governance, security, FinOps, and observability workflows.

It consumes only the unified `Resource` model from Phase 5. Provider-specific raw payloads must not be required outside collectors and normalizers.

## Deterministic Rule Philosophy

Findings are rule-based and reproducible:
- The same resource state produces the same finding result.
- AI is not involved in deciding whether a finding exists.
- Future AI layers may explain findings, summarize impact, or draft reports, but detection remains deterministic.

Each rule declares:
- `rule_id`
- `finding_type`
- `category`
- `severity`
- `evaluate(resource)`

## Finding Lifecycle

Initial statuses:
- `open`
- `acknowledged`
- `resolved`
- `false_positive`

Phase 6 does not auto-resolve findings that disappear from a later run. Findings not seen in the latest run remain open until a later lifecycle policy is implemented safely.

## Severity Model

Initial severities:
- `critical`
- `high`
- `medium`
- `low`
- `informational`

Rules may raise severity based on deterministic context. For example, public exposure on a database is critical, while public exposure on an expected network component such as a public load balancer is medium.

## Current Phase 6 Rules

### Missing Tags

Category: `governance`

Flags resources missing:
- `environment`
- `owner`
- `cost_center`
- `application`

### Public Exposure

Category: `security`

Flags resources with:
- `exposure_level=public`
- public IP metadata
- metadata indicating `0.0.0.0/0`
- public load balancer indicators

### Unattached Volume

Category: `finops`

Flags block storage that appears detached, available, or without attachment metadata.

Recommendations require validation and snapshot language before deletion.

### Idle Compute

Category: `finops`

Flags running compute only when utilization evidence exists:
- CPU average below 5% for 7 or 14 days.

If metrics are missing, no idle finding is created.

### Observability Gap

Category: `observability`

Flags compute, database, and network resources with:
- `monitoring_enabled=false`
- `alarms_count=0`
- no monitoring metadata for prod resources

## Fingerprint And Upsert

Findings use a deterministic fingerprint:

```text
tenant_id + cloud_account_id + provider + resource_id + finding_type + rule_id
```

Upsert behavior:
- Same fingerprint updates the existing finding and `last_seen_at`.
- New fingerprint creates a new finding.
- Existing `first_seen_at` remains stable.
- Duplicate findings are avoided on repeated runs.

## API Layer

Endpoints:
- `POST /api/v1/findings/run`
- `GET /api/v1/findings`
- `GET /api/v1/findings/summary`
- `GET /api/v1/findings/{finding_id}`
- `PATCH /api/v1/findings/{finding_id}/status`

Access:
- ADMIN and ANALYST can run findings.
- ADMIN and ANALYST can update status.
- ADMIN, ANALYST, and VIEWER can list/read findings.

## Known Limitations

- No auto-resolution in Phase 6.
- No risk score yet.
- No AI analysis.
- No reports/dashboard.
- Idle compute requires metrics that collectors may not yet provide.
- Findings depend on normalized resource metadata quality.

## Future Extension Points

- Risk scoring engine.
- Auto-resolution with safe last-seen windows.
- Rule configuration per tenant.
- Suppression/exception policies.
- Evidence enrichment from cloud-native metrics.
- AI explanation/reporting layer that consumes, but does not decide, findings.
