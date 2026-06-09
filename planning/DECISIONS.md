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
