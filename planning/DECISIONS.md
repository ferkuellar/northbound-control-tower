# Architecture Decisions

## ADR-001 — Cloud Shell opt-in via CLOUD_SHELL_ENABLED

**Date:** 2026-06-08
**Status:** Accepted

### Context

Cloud Shell allows operators to execute `nb` commands against cloud infrastructure from inside the application. If the feature were enabled by default, any deployment without explicit configuration would expose this attack surface. Enterprise auditors require a documented opt-in control for privileged execution surfaces.

### Decision

`CLOUD_SHELL_ENABLED` defaults to `False`. Every deployment must explicitly set `CLOUD_SHELL_ENABLED=true` to activate Cloud Shell. The guard fires before authentication, before executor instantiation, and before any audit record is written.

### Consequences

- New deployments have Cloud Shell off without any configuration action.
- Enabling Cloud Shell requires an intentional operational decision per environment.
- The flag does not replace RBAC: roles, allowlists, and audit logging remain active when the flag is `true`.
- Production enablement should be documented in the operational runbook.

---

## ADR-005 — Claude model defaults must be current and environment-overridable

**Date:** 2026-06-08
**Status:** Accepted

### Context

`claude_model` defaulted to `"claude-3-5-sonnet-latest"`, an alias that no longer resolves correctly against the Anthropic API used by the project. If `CLAUDE_MODEL` is not explicitly set in a deployment, the integration fails at runtime with a model-not-found error that can be misdiagnosed as a credential problem.

### Decision

The code default is `"claude-sonnet-4-6"`. Production environments must explicitly set `CLAUDE_MODEL` rather than relying on the code default. The default exists for development and demo use only.

### Consequences

- Development and demo environments work without explicit `CLAUDE_MODEL` configuration.
- A wrong default fails at runtime, not silently — the error is now a known-good model name.
- Production must pin the model explicitly; the code default is a last-resort safety net, not operational configuration.

---

## ADR-004 — AWS RoleSessionName must be traceable

**Date:** 2026-06-08
**Status:** Accepted

### Context

The prior `RoleSessionName` was the hardcoded string `"northbound-control-tower-inventory"` for all assume-role operations. When multiple accounts or operations share the same session name, CloudTrail records in the customer's account are indistinguishable — an auditor cannot determine which operation triggered which API call or which internal user initiated it.

### Decision

All assume-role calls use `build_role_session_name()` which produces `nb-{actor[:8]}-{operation}` (or with `request_number` for apply operations). The actor is the first 8 chars of the internal `user_id`, or `svc` for service-initiated operations. Generic hardcoded session names are prohibited.

### Consequences

- Customer CloudTrail records show `nb-a1b2c3d4-scan` or `nb-svc-scan` in the assumed-role ARN.
- The actor segment is a short opaque identifier (not email, not full UUID) — minimal PII exposure while maintaining internal traceability via `user_id` lookup.
- Inventory collectors currently default to `nb-svc-scan` because `AWSInventoryCollector` does not yet receive a `user_id`. When triggered by a user API call, callers may pass `user_id` to `AWSSessionFactory` to get per-user attribution.
- Apply operations must pass `request_number` via `operation=f"apply-{request.request_number}"` when the provisioning layer integrates cloud sessions (future sprint).

---

## ADR-003 — CORS request headers must be explicitly allowlisted

**Date:** 2026-06-08
**Status:** Accepted

### Context

The CORS configuration used `allow_headers=["*"]`, which permits any request header cross-origin. Enterprise security auditors and automated scanners flag wildcard CORS headers as a finding because they unnecessarily broaden the attack surface and prevent header-level policy enforcement.

### Decision

`allow_headers` uses an explicit list: `Authorization`, `Content-Type`, `X-Tenant-ID`, `X-Request-ID`, `Accept`. Headers were derived from actual backend usage (`middleware/tenant.py`, `observability/middleware.py`) and standard API client needs. New headers must be added only with documented justification.

### Consequences

- Browsers will block cross-origin requests that include unlisted request headers.
- Any new header required by the API must be explicitly added here.
- `allow_headers=["*"]` must not reappear in production-facing configurations.

---

## ADR-002 — Credential encryption at rest via Fernet

**Date:** 2026-06-08
**Status:** Accepted

### Context

Cloud account credentials (access keys, secret keys, OCI private keys) were stored as plaintext in the `cloud_accounts` table. Any database read — backup, replica, misconfigured query — would expose provider credentials directly.

### Decision

Credentials are encrypted with Fernet (AES-128-CBC + HMAC-SHA256) using `CREDENTIAL_ENCRYPTION_KEY` before insert/update (via SQLAlchemy events). `decrypt_credential()` is called only at the point of use in collectors. The key is required in production (validated at startup). The migration converts affected columns to `Text`.

### Consequences

- Credentials are never stored plaintext.
- Key rotation requires re-encrypting existing rows (not automated in this phase).
- Loss of `CREDENTIAL_ENCRYPTION_KEY` means credentials are unrecoverable without backup.
- `decrypt_credential()` must be called explicitly wherever a credential is consumed.
