# SaaS Hardening

## Purpose

Phase 12 hardens Northbound Control Tower as a multi-tenant SaaS platform. The goal is deterministic tenant isolation, permission-based authorization, rate limiting, safer secret access, security middleware, and an auditable control plane.

## Tenant Isolation Model

Authenticated requests carry `tenant_id` in JWT claims. `TenantContextMiddleware` reads the token, attaches `tenant_id` to request state, and rejects explicit `X-Tenant-ID` mismatches.

Service and API queries continue to enforce tenant filtering at query time. Cross-tenant resource reads return `404` instead of leaking existence.

Rules:

- every tenant-owned query must filter by `tenant_id`
- path IDs are always resolved together with `tenant_id`
- cloud credentials and generated artifacts are never returned across tenants

## RBAC Model

Roles remain:

- `ADMIN`
- `ANALYST`
- `VIEWER`

Authorization now uses explicit permissions rather than direct role checks.

Permissions:

- `users:read`
- `users:write`
- `tenants:read`
- `tenants:write`
- `cloud_accounts:read`
- `cloud_accounts:write`
- `inventory:read`
- `inventory:scan`
- `findings:read`
- `findings:write`
- `scores:read`
- `scores:calculate`
- `ai:read`
- `ai:generate`
- `reports:read`
- `reports:generate`
- `audit:read`

## Permission Mapping

`ADMIN` receives all permissions.

`ANALYST` receives operational permissions:

- read tenant context
- manage cloud accounts
- run inventory scans
- read/write findings
- read/calculate scores
- read/generate AI analysis
- read/generate reports

`VIEWER` receives read-only permissions:

- tenant context read
- cloud account read
- inventory read
- findings read
- scores read
- AI read
- reports read

Audit log access is `ADMIN` only through `audit:read`.

## Rate Limiting Strategy

Phase 12 uses an in-memory limiter scoped per backend process.

Default limits:

- login: 5 requests/minute per IP
- AI analysis: 10 requests/minute per user
- report generation: 5 requests/minute per user
- inventory scan: 5 requests/minute per tenant

Exceeded limits return HTTP `429` with `Retry-After`.

Production should move rate limit state to Redis for multi-instance consistency.

## Audit Trail Design

Audit logs now include:

- actor user
- actor role
- tenant
- action
- resource type and ID
- before/after state placeholders
- request ID
- IP address
- user agent
- timestamp

The API endpoint `GET /api/v1/audit/logs` supports filtering by date range, user, action, and resource type. Access requires `audit:read`.

## Secrets Handling Strategy

`backend/security/secrets.py` introduces a provider abstraction. Phase 12 defaults to local environment variables and keeps a pluggable boundary for future vaults:

- AWS Secrets Manager
- OCI Vault
- Azure Key Vault

Cloud account database-stored credentials remain technical debt for local development. Production must move cloud credentials to vault-backed storage or role-based access with external IDs.

## Security Middleware

Security middleware adds:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 0`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy`
- HTTPS-only HSTS when request scheme is HTTPS

Request validation rejects oversized request bodies and unsupported content types for write methods.

## Known Limitations

- Rate limits are process-local in Phase 12.
- Database-stored cloud credentials are not encrypted yet.
- SSO and MFA are intentionally out of scope.
- Tenant isolation relies on consistent query-level enforcement until a future repository layer or database row-level security is introduced.

## Future Improvements

- Redis-backed distributed rate limiting.
- Database row-level security for tenant-owned tables.
- Vault-backed cloud credentials.
- SSO and MFA.
- Dedicated user management API.
- External SIEM export after log schema stabilizes.
