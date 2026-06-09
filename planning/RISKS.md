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

## RISK-004 — Inventory scans show nb-svc-scan until callers pass user_id

**Severity:** Low
**Likelihood:** N/A (accepted limitation)
**Status:** Tracked — known gap, not a security risk

**Description:** `AWSInventoryCollector` instantiates `AWSSessionFactory` without a `user_id`. All scan-triggered assume-role calls appear as `nb-svc-scan` in customer CloudTrail. This limits per-user attribution in the customer's audit trail for inventory operations.

**Mitigation applied:** `AWSSessionFactory` accepts optional `user_id` and `operation` parameters. Service-initiated calls default to `svc`.

**Residual risk:** Customer cannot distinguish which internal user triggered a scan unless the caller propagates `user_id` to the factory.

**Recommended next control:** When scan API endpoints are added, propagate the authenticated user's `user_id` to `AWSInventoryCollector` → `AWSSessionFactory`.

---

## RISK-005 — Terraform apply path does not yet use AWSSessionFactory

**Severity:** Medium
**Likelihood:** N/A (current architecture)
**Status:** Tracked — architecture gap for future sprint

**Description:** `TerraformApplyService` runs `terraform apply` via subprocess with a locked-down `PATH`-only env. It does not call `sts.assume_role()`. When the provisioning layer evolves to make direct AWS API calls (e.g., post-apply validation, rescan), it will need to call `AWSSessionFactory` with `operation=f"apply-{request.request_number}"` for full CloudTrail traceability.

**Recommended next control:** When provisioning services add direct AWS SDK calls, use `AWSSessionFactory(account, user_id=..., operation=f"apply-{request.request_number}")`.

---

## RISK-009 — Misconfigured customer IAM roles can block apply or grant excessive permissions

**Severity:** Medium
**Likelihood:** Medium (new onboarding surface)
**Status:** Active — requires customer-side validation

**Description:** The separation of `role_arn` (read-only) and `remediation_role_arn` (write) is enforced in the application, but the actual IAM policies in the customer's AWS account are outside Northbound's control. A customer could configure `remediation_role_arn` with `AdministratorAccess`, widening blast radius beyond what templates require. Conversely, a misconfigured role without the required permissions will cause `terraform apply` to fail after precheck.

**Mitigation applied:**
- `TerraformApplyService` blocks apply if `remediation_role_arn` is not configured.
- `get_aws_remediation_session()` enforces the guard at the session layer.
- No silent fallback from remediation role to read-only role.
- CloudTrail session names include operation label for attribution.

**Residual risk:** Northbound cannot enforce the exact IAM policy content attached to customer-managed roles. Excessive permissions in `remediation_role_arn` are invisible at the application layer.

**Recommended next control:** Add customer IAM policy validation during onboarding: verify `role_arn` has only read permissions (e.g., `ReadOnlyAccess`) and `remediation_role_arn` is scoped to the minimum required actions for each Terraform template.

---

## RISK-008 — Seed demo data must not reach production environments

**Severity:** Medium
**Likelihood:** Low (requires manual execution in the wrong environment)
**Status:** Active — requires operational discipline

**Description:** `scripts/seed_demo_data.py` creates a demo tenant with a known password (`DemoPass123!`), a fictitious AWS account ARN, and synthetic resources/findings/scores. If executed against a production database, it would create a backdoor admin account and pollute operational data.

**Mitigation applied:**
- Script docstring explicitly prohibits production use.
- `DemoPass123!` is not a valid or useful production credential.
- Script is excluded from startup automation.
- Password is documented as demo-only throughout the codebase.

**Residual risk:** No technical guard prevents running the script against a production DATABASE_URL. Operational process must ensure the script is only run in local/dev/demo environments.

**Recommended next control:** Add a guard at script startup that checks `APP_ENV` and refuses to run if `APP_ENV=production`.

---

## RISK-007 — Celery worker healthcheck does not validate end-to-end task execution

**Severity:** Low
**Likelihood:** Medium (queue issues can occur without worker crash)
**Status:** Active — accepted for this phase

**Description:** `celery inspect ping` confirms the worker process is alive and responding through the broker. It does not validate that tasks are being dequeued, executed, or completing successfully. A worker can be "healthy" by this metric while a queue accumulates, tasks fail silently, or specific task types are stuck.

**Mitigation applied:**
- Worker healthcheck added; Docker can detect crashed or hung workers.
- Celery task metrics are instrumented (`CELERY_TASKS_TOTAL`, `CELERY_TASK_DURATION_SECONDS`) for Prometheus via `workers/celery_app.py`.

**Residual risk:** No queue depth alerting, failed task count threshold, or task latency monitoring exists yet.

**Recommended next control:** Add queue depth and failed task count to Prometheus/Grafana dashboards. Set alert thresholds for queue depth and task failure rate in a future operations sprint.

---

## RISK-006 — CSP baseline still allows unsafe-inline

**Severity:** Medium
**Likelihood:** Low (no known XSS vector)
**Status:** Active — accepted for this phase

**Description:** The `Content-Security-Policy` baseline permits `'unsafe-inline'` for both `script-src` and `style-src` to maintain compatibility with xterm and current frontend bundles. `'unsafe-inline'` limits the protection CSP provides against injected scripts — a successful XSS can still execute inline code.

**Mitigation applied:**
- CSP baseline is set; absence-of-header finding is resolved for auditors.
- `default-src 'self'` blocks external resource loading.
- `frame-ancestors 'none'` supplements `X-Frame-Options: DENY`.
- Cloud Shell is disabled by default (ADR-001), reducing XSS blast radius.

**Residual risk:** `'unsafe-inline'` reduces the effectiveness of CSP against DOM-based and reflected XSS attacks.

**Recommended next control:** In a future sprint, audit frontend bundle for inline script/style requirements and migrate to nonce-based or hash-based CSP. Remove `'unsafe-inline'` once compatibility is confirmed.

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
