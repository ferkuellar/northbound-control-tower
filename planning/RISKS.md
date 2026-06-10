# Risk Register

## RISK-016 — BACKEND_CORS_ORIGINS must be updated when the production frontend domain changes

**Severity:** Medium
**Likelihood:** Low (but silent when it happens)
**Status:** Active — requires operational discipline

**Description:** The production CORS allowlist is static configuration. If the frontend domain changes (e.g., custom domain, rebrand, new CDN endpoint) and `BACKEND_CORS_ORIGINS` is not updated, all browser requests from the new domain will fail with CORS errors. The backend remains healthy and logs no application error — the failure is visible only in the browser console and network tab.

**Mitigation applied:**
- Production startup blocks localhost origins — misconfigured localhost deployments are caught at boot.
- `.env.example` documents the production example value.

**Residual risk:** A domain change after deployment requires a config update and restart. No automated detection exists for stale CORS configuration.

**Recommended next control:** Add a CORS health probe to smoke tests that verifies the configured origins match the expected production domain after each deployment.

---

## RISK-015 — CI pipeline validates basic quality only; no security scanning, migration tests, or deployment verification

**Severity:** Low
**Likelihood:** N/A (known scope limitation)
**Status:** Active — accepted for this phase

**Description:** The initial CI pipeline (`ci.yml`) covers backend lint/tests and frontend lint/build. It does not cover: SAST/dependency scanning, Docker image builds, database migration rollback tests, E2E tests, or any deployment verification. A change could pass CI and still introduce a silent security issue, a broken Docker image, or a migration that applies but cannot roll back.

**Mitigation applied:**
- Alembic migrations run against a live PostgreSQL 16 service in CI — migration correctness is tested on every push.
- `ruff check` catches obvious security anti-patterns (e.g., hardcoded strings flagged by rules).
- Full test suite (312 tests) runs on every push, covering encryption, secret provider, CORS, CSP, and auth paths.

**Residual risk:** No SAST, no dependency vulnerability scan, no Docker image smoke test.

**Recommended next control:** Add `pip-audit` or `trivy` for dependency scanning in a future sprint. Add CodeQL after initial CI stabilizes.

---

## RISK-014 — OCI Vault provider requires cloud-side configuration not yet validated end-to-end

**Severity:** Medium
**Likelihood:** High (any production deployment before OCI onboarding)
**Status:** Active — production deployment blocked until OCI Vault is configured

**Description:** `OCIVaultSecretProvider` implements the OCI Vault lookup flow (vault → compartment → secret bundle → base64 decode) but has not been tested against a live OCI environment. It requires: a valid `~/.oci/config` or instance/resource principal authentication, an active OCI Vault OCID, IAM policies granting `SECRET_BUNDLE_READ` on the vault, and secrets pre-loaded with the correct names. Until this is validated, production deployment remains blocked (startup raises `RuntimeError` without `OCI_VAULT_ID`).

**Mitigation applied:**
- Production startup fails fast if `OCI_VAULT_ID` is not set.
- `get_secret_provider()` raises before any `.env` fallback occurs.
- All tests use mocks — no real OCI calls are made.

**Residual risk:** Until a live OCI Vault is configured and the end-to-end flow is validated, production cannot start. This is intentional — the alternative (silent `.env` fallback) is worse.

**Recommended next control:** Validate the OCI Vault provider end-to-end in a staging environment. Document the required IAM policy and secret naming conventions in `docs/OPERATIONS.md`.

---

## RISK-013 — External scripts referencing the removed root terraform-catalog/ path will fail

**Severity:** Low
**Likelihood:** Low (no external scripts found referencing the root path)
**Status:** Mitigated — accepted residual

**Description:** The root `terraform-catalog/` directory has been deleted. Any script, CI step, or documentation that still references `./terraform-catalog/` or `/terraform-catalog/` will break with a "path not found" error. A search of all files found only one historical audit document (`docs/audits/terraform-validate-plan-audit.md`) referencing the root path — no operational scripts were affected.

**Mitigation applied:**
- Root `terraform-catalog/` deleted; `backend/terraform-catalog/` is the sole catalog.
- `_detect_repo_root()` updated to always resolve paths relative to `backend/`, eliminating dual-path logic.
- All tests pass after the change.

**Residual risk:** If a future developer adds a script outside `backend/` that references `terraform-catalog/` from the repo root, it will fail. The correct path is `backend/terraform-catalog/`.

**Recommended next control:** No action required. Fast-fail on missing path is the correct behavior.

---

## RISK-012 — Alembic must be invoked from backend/ or with explicit -c flag

**Severity:** Low
**Likelihood:** Low (Docker compose enforces correct workdir)
**Status:** Mitigated — accepted residual

**Description:** With only `backend/alembic.ini` remaining, running `alembic` from the repository root without `-c backend/alembic.ini` will produce a "can't find config file" error. This is a fast-fail, not a silent wrong-config execution. Developers unfamiliar with the layout may be confused until they read the docs.

**Mitigation applied:**
- Root `alembic.ini` deleted — no silent wrong-config scenario.
- All documented commands use `docker compose run --rm backend alembic ...` which runs inside the container at `/app` (the backend workdir).
- `CLAUDE.md` documents `cd backend && alembic revision --autogenerate`.

**Residual risk:** A developer running `alembic` from the repository root gets a clear error. Recovery is: `cd backend && alembic <command>` or `alembic -c backend/alembic.ini <command>`.

**Recommended next control:** No action required — fast-fail on missing config is the correct behavior.

---

## RISK-011 — Prompt evaluator checks structure and heuristics, not factual correctness

**Severity:** Medium
**Likelihood:** Medium (any time context data is sparse or wrong)
**Status:** Active — accepted for this phase

**Description:** `scripts/test_prompts.py` verifies that the AI output has the required structure, risk levels from a valid set, minimum text lengths, absence of technical jargon in `one_line`, non-empty risk lists, numeric scores, and the presence of `risk_if_skipped`. It does not verify that the values are factually correct relative to the source context. A response can pass 13/13 while containing invented resources, wrong scores, or fabricated risks — as long as the shape and length heuristics are satisfied.

**Mitigation applied:**
- `SYSTEM_PROMPT` and prompt rules explicitly prohibit inventing data not present in the provided context.
- `validate_ai_output()` in `ai/validators.py` checks for limitation signals when resources are unavailable.
- The evaluator is documented as a structural check, not a factual validation.

**Residual risk:** 13/13 is a necessary but not sufficient condition for output quality. Enterprise reports still require source-context validation (verifying that values in the output are traceable to context data) and human review before delivery.

**Recommended next control:** Add source-context validation that cross-references key output values (e.g., score values, top finding titles) against the input context used to generate the response. Pair with human review for customer-facing reports.

---

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

## RISK-010 — Few-shot examples and explicit schemas increase prompt size and truncation risk

**Severity:** Medium
**Likelihood:** Low (current analysis types are within token budget)
**Status:** Active — monitor

**Description:** `EXECUTIVE_SUMMARY_SCHEMA` and `EXECUTIVE_SUMMARY_EXAMPLE` add approximately 1500–2000 tokens to the `executive_summary` user prompt. For `full_assessment` (which combines all analysis types) this could push the prompt near or past the effective context window when the cloud context is large (many resources/findings/scores).

**Mitigation applied:**
- `AI_MAX_TOKENS=4000` and `AI_REQUEST_TIMEOUT_SECONDS=90` are set as defaults.
- `AIContextBuilder` limits input to 50 findings and 100 resources (`AI_MAX_INPUT_FINDINGS`, `AI_MAX_INPUT_RESOURCES`).
- `executive_summary` is the only prompt currently upgraded; other analysis types use `BASE_RULES` (shorter).

**Residual risk:** `full_assessment` concatenates all sections and does not have per-section schemas yet. A large context + expanded schema + example could cause Claude to truncate structured JSON or produce incomplete `recommendations_30_60_90`.

**Recommended next control:** Add per-analysis-type token budget estimation before prompt dispatch. Consider sectioned generation for `full_assessment` (one section per call) in a future sprint.

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
