# Architecture Decisions

## ADR-012 — AWS CloudAccount must separate read-only collector role from write-capable remediation role

**Date:** 2026-06-09
**Status:** Accepted

### Context

Collectors, inventory scans, findings, and scoring require only read access. Terraform apply/remediation requires write access to specific AWS resources. Using the same IAM role for both violates least privilege: a bug or abuse in a passive scan flow could gain write-capable permissions, and CloudTrail audit trails lose operational separation.

### Decision

`CloudAccount` carries two distinct role ARN fields: `role_arn` (read-only, `northbound-readonly`) used by all collectors and inventory operations, and `remediation_role_arn` (write, `northbound-remediation`) used exclusively by Terraform apply/remediation flows. `TerraformApplyService` raises `ValueError` with an explicit message if `remediation_role_arn` is not configured — there is no silent fallback to `role_arn`. `get_aws_readonly_session()` and `get_aws_remediation_session()` are the canonical helpers; the latter enforces the guard.

### Consequences

- Collectors cannot accidentally use a write-capable role.
- Terraform apply cannot proceed without an explicitly configured remediation role.
- Customers must configure two IAM roles during onboarding; the exact IAM policy content is a future sprint.
- CloudTrail will show distinct role session names for scans (`nb-svc-scan`) and apply (`nb-svc-apply` or per-user).

---

## ADR-011 — AI demos require seeded context data; empty database must not be used for provider quality evaluation

**Date:** 2026-06-09
**Status:** Accepted

### Context

`AIContextBuilder` reads Tenant, CloudAccount, Resource, Finding, and CloudScore from the database. With an empty database, the AI context carries zero resources, zero findings, and no scores. Claude produces low-value analysis against empty context, `validate_ai_output()` may reject the output for missing limitation signals, and test results for `/api/v1/ai/analyze` are misleading.

### Decision

A `scripts/seed_demo_data.py` script provides minimal but realistic demo context for local AI testing. The script is idempotent across multiple runs via per-run unique slugs and emails. It must never be run against production environments and must never be treated as production data.

### Consequences

- Claude smoke tests and end-to-end demos run against realistic multi-finding, multi-score context.
- Each `seed()` call creates an independent demo tenant, so multiple demo datasets can coexist.
- The script does not modify migrations, models, or production configuration.

---

## ADR-010 — All long-running worker services must include Docker healthchecks

**Date:** 2026-06-09
**Status:** Accepted

### Context

The Celery worker service had no Docker healthcheck. Docker Compose treats a service without a healthcheck as permanently healthy as soon as the process starts, even if the worker crashes, hangs, or loses broker connectivity. Downstream services (or operators) cannot detect a silent worker failure from container metadata alone.

### Decision

All long-running worker services must include a Docker healthcheck. Celery workers use `celery inspect ping` as the baseline health signal, using the same `-A` path as the worker's startup command. The healthcheck confirms the worker process is alive and reachable through the broker.

### Consequences

- Docker and orchestrators can detect dead/hung workers and restart them automatically.
- `docker compose ps` reflects real worker liveness, not just process presence.
- `celery inspect ping` does not validate end-to-end task execution; queue depth, failed task tracking, and latency monitoring are still required for production observability.

---

## ADR-009 — Backend responses must include a baseline Content-Security-Policy

**Date:** 2026-06-09
**Status:** Accepted

### Context

`SecurityHeadersMiddleware` set `X-Frame-Options` and `X-Content-Type-Options` but no `Content-Security-Policy`. Enterprise auditors flag the absence of CSP regardless of other controls. Cloud Shell, command execution, and terminal components (xterm) increase the blast radius of any XSS — a CSP header reduces that surface even at baseline.

### Decision

`SecurityHeadersMiddleware` adds `Content-Security-Policy` via `response.headers.setdefault()`. The baseline policy restricts sources to `'self'` while temporarily allowing `'unsafe-inline'` for frontend/xterm compatibility. `setdefault` ensures a stricter upstream policy from a proxy, CDN, or gateway is never downgraded by the application.

### Consequences

- Backend responses carry a CSP header that satisfies enterprise audit findings.
- `'unsafe-inline'` remains a residual risk; future hardening must move to nonce/hash-based policies.
- `frame-ancestors 'none'` reinforces anti-clickjacking alongside the retained `X-Frame-Options: DENY`.
- Adding new frontend resource origins (fonts, CDN assets, WebSocket) requires extending the policy.

---

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

## ADR-008 — AI defaults must preserve safe startup while supporting reliable demos

**Date:** 2026-06-08
**Status:** Accepted

### Context

`AI_PROVIDER=none` is correct as a safe default, but without documented activation steps and correct defaults for `AI_MAX_TOKENS` (was 2500) and `AI_REQUEST_TIMEOUT_SECONDS` (was 60), demo environments frequently produce truncated JSON or timeout errors. These failures are misdiagnosed as provider or key problems.

### Decision

Code defaults: `ai_max_tokens=4000`, `ai_request_timeout_seconds=90`. `.env.example` documents how to activate Claude in development/demo with explicit comments. `AI_PROVIDER=none` and `ANTHROPIC_API_KEY=` remain empty as safe defaults. Production must configure all AI settings explicitly.

### Consequences

- Development/demo environments get reliable Claude responses with fewer truncation failures.
- `AI_PROVIDER=none` still prevents accidental AI activation on fresh deploys.
- Production must pin `AI_MAX_TOKENS` and `AI_REQUEST_TIMEOUT_SECONDS` based on prompt size, latency, and cost — the code defaults are not production guidance.

---

## ADR-007 — AI limitation validation must accept a controlled set of semantic signals

**Date:** 2026-06-08
**Status:** Accepted

### Context

`validate_ai_output()` previously required the exact word `"limitation"` to accept an AI response when resource context was missing. Claude and other models legitimately express the same intent using phrases like `"no data available"`, `"constraint"`, `"missing data"`, `"incomplete"`, `"unavailable"`, etc. The rigid check caused valid responses to be rejected with `AIOutputValidationError`.

### Decision

The validator uses a `LIMITATION_SIGNALS` tuple as the authoritative vocabulary. Any signal in that set is sufficient to satisfy the limitation acknowledgment requirement. The set is defined as a named constant so it can be reviewed, extended, or referenced in tests without changing validator logic.

### Consequences

- Valid model responses are no longer rejected for wording differences.
- The validator remains strict: outputs with none of the signals and `resources_available=False` still raise `AIOutputValidationError`.
- Adding new signals requires only updating `LIMITATION_SIGNALS` — no logic change.
- This does not replace a future structural approach where the model returns a `limitations` key in JSON.

---

## ADR-006 — ClaudeProvider must use a system message requiring JSON-only responses

**Date:** 2026-06-08
**Status:** Accepted

### Context

Without a `system` message, Claude may wrap JSON in markdown fences, add preamble text, or include explanations outside the JSON object. When this happens, `parse_ai_output()` cannot recover the structured fields (`executive_summary`, `technical_assessment`, etc.) and degrades the response to `{"analysis_text": "..."}`, breaking UI, reports, dashboards and validators.

### Decision

`ClaudeProvider.generate_analysis()` sends a `system` message that explicitly requires valid JSON only, prohibits markdown fences and preamble, requires the entire response to be parseable by `json.loads()`, and prohibits inventing data not present in the provided context.

### Consequences

- The probability of unstructured or markdown-wrapped responses is significantly reduced.
- The system message does not guarantee 100% compliance; output validation remains necessary.
- The prompt text is currently inline in `claude.py`. A future sprint should move it to `ai/prompts.py` to be versioned alongside prompt schemas.

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
