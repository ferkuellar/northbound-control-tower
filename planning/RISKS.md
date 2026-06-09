# Risk Register

## RISK-001 — Cloud Shell active in unreviewed environments

**Severity:** High
**Likelihood (before mitigation):** Medium
**Status:** Mitigated

**Description:** Cloud Shell allows execution of `nb` commands against cloud infrastructure. If enabled without operational review, an operator or compromised account could interact with cloud resources without explicit deployment approval.

**Mitigation applied:**
- `CLOUD_SHELL_ENABLED` defaults to `False` (ADR-001).
- Guard fires before authentication and before executor instantiation.
- `.env.example` documents `CLOUD_SHELL_ENABLED=false` with an explicit note.

**Residual risk:**
- A misconfigured deployment that sets `CLOUD_SHELL_ENABLED=true` without review still exposes the surface.
- No automated enforcement prevents enabling in production without approval workflow.

**Recommended next control:** Require `CLOUD_SHELL_ENABLED=true` to be gated behind an additional `CLOUD_SHELL_APPROVAL_TOKEN` or equivalent operational approval mechanism in a future sprint.

---

## RISK-002 — Credential encryption key loss

**Severity:** Critical
**Likelihood:** Low
**Status:** Active

**Description:** `CREDENTIAL_ENCRYPTION_KEY` is the single point of recovery for all encrypted cloud credentials. If lost or rotated without re-encryption, all stored credentials become unrecoverable without a backup.

**Mitigation applied:**
- Key is required in production (startup validation fails if absent).
- Fernet provides authenticated encryption (tampered ciphertext is rejected).

**Residual risk:**
- No automated key rotation or re-encryption workflow exists.
- Backup and recovery procedure for the key is not yet documented.

**Recommended next control:** Document key backup procedure in OPERATIONS.md; evaluate envelope encryption with a KMS for production.

---

## RISK-003 — Terraform apply surface not gated at command level

**Severity:** High
**Likelihood:** Low (currently NOT_IMPLEMENTED)
**Status:** Tracked

**Description:** `nb terraform apply` is registered in the command registry but returns `NOT_IMPLEMENTED`. When implemented, it must require: persisted provisioning request, Terraform plan artifact, security scan, cost estimate, human approval, post-remediation validation, and evidence attachment.

**Mitigation applied:**
- `TERRAFORM_APPLY_ENABLED` defaults to `False`.
- Command returns `NOT_IMPLEMENTED` until the full approval workflow is in place.

**Residual risk:**
- The registry entry exists and could be enabled prematurely.

**Recommended next control:** Implement approval workflow (roadmap #24 → #25) before enabling Terraform apply.
