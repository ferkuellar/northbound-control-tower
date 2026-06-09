# Project State

_Last updated: 2026-06-08 (prompt evaluator sprint)_

## Completed

### Security Sprint (2026-06-08)

**Credential encryption at rest** (`security: encrypt cloud account credentials at rest`)
- `security/encryption.py` — Fernet encrypt/decrypt helpers
- `models/cloud_account.py` — SQLAlchemy `before_insert`/`before_update` events
- `core/config.py` — `credential_encryption_key` field
- `collectors/aws/session.py`, `collectors/oci/session.py` — `decrypt_credential()` at consumption
- `alembic/versions/0017_encrypt_credential_columns.py` — columns migrated to `Text`
- `api/main.py` — startup validation for production
- `tests/test_credential_encryption.py` — 13 tests
- Result: 144 passed

**Cloud Shell feature flag** (`security: disable cloud shell by default behind feature flag`)
- `core/config.py` — `cloud_shell_enabled: bool = Field(default=False)`
- `cloud_shell/router.py` — guard before auth and executor, WebSocket close 1008
- `.env.example` — `CLOUD_SHELL_ENABLED=false` with operational comment
- `tests/test_cloud_shell.py` — 5 feature flag tests added
- Result: 159 passed

**AI Claude environment defaults** (`ai: update claude environment defaults for structured output`)
- `core/config.py` — `ai_max_tokens` default: 2500 → 4000; `ai_request_timeout_seconds` default: 60 → 90
- `.env.example` — AI section reestructurada con comentarios de activación, valores alineados
- `tests/test_production_secrets.py` — 5 tests de configuración AI agregados (tokens, timeout, provider, key check)
- Result: 212 passed, 1 skipped

**AI limitation validator semantic signals** (`ai: accept semantic limitation signals in output validator`)
- `ai/validators.py` — `LIMITATION_SIGNALS` constant; rigid `"limitation"` check → multi-signal `any()`
- `tests/test_ai_validators.py` — creado, 19 tests (8 signals, case-insensitive, invalid, resources_available, no-regression)
- Result: 208 passed

**Claude provider JSON-only system message** (`ai: force claude provider to return json only`)
- `ai/providers/claude.py` — `system=` message agregado a `client.messages.create()`
- `tests/test_claude_provider.py` — creado, 8 tests (system presence, content, params, text extraction, non-text blocks, missing key)
- Result: 189 passed

**Claude model default updated** (`ai: update default claude model configuration`)
- `core/config.py` — `claude_model` default: `claude-3-5-sonnet-latest` → `claude-sonnet-4-6`
- `.env.example` — `CLAUDE_MODEL` alineado al mismo valor
- `tests/test_production_secrets.py` — 3 tests de configuración AI agregados
- Result: 181 passed

**Traceable AWS role session names** (`security: add traceable aws role session names`)
- `collectors/aws/session.py` — `build_role_session_name()` helper; `AWSSessionFactory` accepts `user_id` and `operation`; hardcoded `"northbound-control-tower-inventory"` eliminated
- `tests/test_aws_session.py` — 13 tests (helper formats, assume_role mock, defensive check)
- Result: 178 passed

**CORS header allowlist** (`security: replace wildcard cors headers with explicit allowlist`)
- `api/main.py` — `allow_headers=["*"]` replaced with explicit list (Authorization, Content-Type, X-Tenant-ID, X-Request-ID, Accept)
- `tests/test_saas_hardening.py` — 6 CORS preflight tests added
- Result: 165 passed

**AI demo seed data script** (`ai: add demo seed data script for ai context testing`)
- `backend/scripts/seed_demo_data.py` — creado; tenant, user, cloud account, 2 resources, 3 findings, 3 scores
- `backend/tests/test_seed_demo_data.py` — 7 tests (tenant, user, password hash, resources, findings, scores, collision)
- Diferencias vs guía: `Finding.rule_id` requerido; `CloudScore.summary` requerido; sin `formula_version`/`findings_count`/`weights_used`/`domain_scores`
- ADR-011, RISK-008 documentados
- Result: 223 passed, 1 skipped (3 fallos pre-existentes en test_reporting_engine por rate limit Redis compartido — no relacionados)

**Measurable prompt evaluation script** (`ai: add measurable prompt evaluation script`)
- `scripts/test_prompts.py` — created; `check_executive_summary()` returning stable 13 criteria; `evaluate()` dispatcher; `main()` CLI with `--type`, `--file`, `--save`, `--strict`
- `tests/test_test_prompts.py` — created; 24 tests (criterion count stability, valid output 13/13, individual failures, incomplete output never skips criteria, CLI --file, CLI --strict)
- ADR-014, RISK-011 documented
- Result: 294 passed, 3 skipped

**AI executive summary prompt schema** (`ai: add explicit executive summary prompt schema`)
- `ai/prompts.py` — `PROMPT_VERSION` → `"phase9-v1.1"`; `SYSTEM_PROMPT` (Principal Cloud Architect, CISO/CFO, JSON-only, safety rules); `EXECUTIVE_SUMMARY_SCHEMA` (fixed 6-section structure); `EXECUTIVE_SUMMARY_EXAMPLE` (few-shot, fictitious, do-not-copy warning); `executive_summary_prompt()` rebuilt to include schema + example + version
- `ai/providers/claude.py` — imports and uses `SYSTEM_PROMPT` from `ai.prompts`; hardcoded system string removed
- `tests/test_ai_prompts.py` — created; 31 tests (PROMPT_VERSION, SYSTEM_PROMPT content, schema structure, example content, prompt integration, other types)
- `tests/test_claude_provider.py` — 1 new test: `test_system_message_is_imported_system_prompt`
- `BASE_RULES` retained for non-`executive_summary` analysis types
- ADR-013, RISK-010 documented
- Result: 270 passed, 3 skipped

**AWS role separation: readonly vs remediation** (`security: separate readonly and remediation aws roles`)
- `models/cloud_account.py` — `remediation_role_arn: Mapped[str | None]` added after `role_arn`
- `alembic/versions/2026_06_09_0900-0018_remediation_role_arn.py` — migration created; roundtrip verified
- `api/schemas/inventory.py` — `AWSCloudAccountCreate` + `CloudAccountRead` expose `remediation_role_arn`
- `api/routes/cloud_accounts.py` — `remediation_role_arn` passed on AWS account creation
- `collectors/aws/session.py` — `role_arn_override` param; `get_aws_readonly_session()` and `get_aws_remediation_session()` helpers; guard raises if `remediation_role_arn` is None
- `provisioning/terraform_apply_service.py` — `_assert_remediation_role()` guard fires before precheck; raises `ValueError` with explicit message; no fallback to `role_arn`
- `tests/test_aws_session.py` — 8 new tests (readonly uses role_arn, remediation uses remediation_role_arn, raises on None, no fallback, operation label, source scan)
- `tests/test_terraform_apply_service.py` — created; 6 tests (raises on missing, error message, proceeds on set, skips when no cloud_account_id, no fallback, source scan)
- ADR-012, RISK-009 documented
- Result: 238 passed, 3 skipped (pre-existing rate limit skips)

**Celery worker Docker healthcheck** (`infra: add celery worker healthcheck`)
- `docker-compose.yml` — `healthcheck` agregado al servicio `worker` usando `celery inspect ping`
- Verificado: `docker compose config` ✅, worker muestra `(healthy)` en `docker compose ps`
- ADR-010, RISK-007 documentados

**Baseline Content-Security-Policy** (`security: add baseline content security policy header`)
- `security/headers.py` — `Content-Security-Policy` via `setdefault` in `SecurityHeadersMiddleware`
- `tests/test_saas_hardening.py` — 4 tests agregados (CSP present, directives, headers preserved, setdefault no-overwrite)
- Result: 216 passed, 1 skipped

## Roadmap Queue

Priority order per CLAUDE.md:

| # | Item | Status |
|---|------|--------|
| 27 | (next) | pending |
| 9  | | pending |
| 24 | | pending |
| 25 | | pending |
| 26 | | pending |
| 29 | | pending |
| 30 | | pending |

## Test Suite Baseline

- **294 passed, 3 skipped** as of 2026-06-08 (prompt evaluator sprint)
- No known failures or skips
- Warning: `passlib` uses deprecated `crypt` module (Python 3.12); no functional impact

## Active Risks

See `planning/RISKS.md` — RISK-002 (key loss), RISK-003 (terraform apply), RISK-006 (CSP unsafe-inline), RISK-009 (IAM role misconfiguration), RISK-010 (prompt truncation), and RISK-011 (evaluator structural only, not factual) are tracked open.
