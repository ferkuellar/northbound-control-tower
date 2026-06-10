# Project State

_Last updated: 2026-06-09 (ai async celery)_

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

**Production secret provider abstraction** (`security: add production secret provider abstraction`)
- `security/secrets.py` — `OCIVaultSecretProvider` added (lazy OCI import, vault→compartment→bundle→base64 flow, 404 guard, no secret logging); `get_secret_provider()` updated with production/development split; production without `OCI_VAULT_ID` raises `RuntimeError`
- `core/config.py` — `oci_vault_id: str | None` and `secret_provider: str = "env"` added
- `api/main.py` — `_validate_production_secrets()` extended: production without `OCI_VAULT_ID` raises at startup
- `.env.example` — `OCI_VAULT_ID=` and `SECRET_PROVIDER=env` documented with comments; no real OCIDs
- `tests/test_production_secrets.py` — `test_production_with_strong_secret_passes` updated to include `oci_vault_id`
- `tests/test_secrets_provider.py` — created; 18 tests covering EnvSecretProvider, development/test/local get_secret_provider, production raises without vault, production returns OCI provider with vault, OCI constructor, region injection, no-SDK raises, get_secret happy path, empty result, 404 handling, no-log assertion, startup validation guard, .env.example check
- ADR-017, RISK-014 documented
- Result: 312 passed, 4 skipped

**Duplicate root Terraform catalog removed** (`repo: remove duplicate root terraform catalog`)
- `terraform-catalog/` (root, 5 files) — deleted via `git rm -r`
- `backend/terraform-catalog/` — sole source of truth; `backend/terraform-catalog/local/noop-validation/` preserved
- `backend/provisioning/terraform_workspace.py` — `_detect_repo_root()` simplified to always return `backend_root`; dual-path host/Docker logic removed
- 16/16 Terraform tests pass; 294/294 suite pass
- ADR-016, RISK-013 documented
- No templates modified; no migrations generated

**Duplicate root Alembic config removed** (`repo: remove duplicate root alembic config`)
- `alembic.ini` (root) — deleted via `git rm`
- `backend/alembic.ini` — sole source of truth; `alembic current` confirmed at `0018_remediation_role_arn (head)`
- ADR-015, RISK-012 documented
- No migrations generated; no models changed

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

**CORS localhost guard in production** (`infra: fail fast on localhost cors in production`)
- `api/main.py` — `_validate_production_secrets()` extended: `"localhost" in settings.backend_cors_origins_raw.lower()` raises `RuntimeError` when `APP_ENV=production`
- `.env.example` — `BACKEND_CORS_ORIGINS` updated from `http://localhost:3000` to `https://app.northbound.io` with production/dev examples documented
- `docker-compose.yml` — not modified; `:-http://localhost:3000` fallback intentionally kept (compose is local/dev only)
- `tests/test_production_secrets.py` — 7 new tests: localhost raises, error text, real domain passes, dev passes, test env passes, mixed list raises, case-insensitive raises; `backend_cors_origins_raw` added to existing production pass test
- `tests/test_secrets_provider.py` — `backend_cors_origins_raw` added to `test_production_validate_passes_with_oci_vault_id`
- ADR-019, RISK-016 documented
- Result: 319 passed, 4 skipped

**Baseline CI pipeline** (`ci: add baseline github actions pipeline`)
- `.github/workflows/ci.yml` — created; two jobs: `backend` (Python 3.12 + PostgreSQL 16 service + ruff + pytest) and `frontend` (Node 22 + npm ci + eslint + next build)
- PostgreSQL 16 service spun up in CI backend job; Alembic `upgrade head` runs before tests
- `CREDENTIAL_ENCRYPTION_KEY` in CI: deterministic URL-safe base64 Fernet dummy — `Y2ktdGVzdC1rZXktZG8tbm90LXVzZS1pbi1wcm9kISE=` — not a real secret
- Defensive scan: no cloud secrets, no API keys, no `terraform apply` in workflow
- ADR-018, RISK-015 documented
- YAML validated: `workflow yaml ok`

**AI async Celery analysis** (`ai: run analysis jobs asynchronously with celery`)
- `ai/enums.py` — `AIAnalysisStatus.RUNNING` added
- `ai/schemas.py` — `AIAnalysisJobAccepted` pydantic model added
- `ai/service.py` — `create_pending()` and `resume_pending()` added; `AIAnalysisType` imported; `generate()` retained for backward compat
- `workers/tasks.py` — CREATED: `run_ai_analysis` Celery task (`ai.run_analysis`, `bind=True`, `max_retries=2`, late imports, `finally: db.close()`)
- `api/routes/ai.py` — `POST /analyze` changed from 201 synchronous to 202 + `create_pending()` + `run_ai_analysis.delay()`
- `tests/test_ai_phase9.py` — `test_analyst_can_generate_ai_analysis` and `test_ai_analysis_list_is_tenant_isolated` updated for 202 + pending contract; `_make_noop_task()` helper added
- `tests/test_ai_async.py` — CREATED: 26 tests covering route 202, create_pending, resume_pending (running→completed→failed), Celery task, polling, rate limit fixture
- ADR-022, RISK-019 documented
- Result: 338 passed, 4 skipped

**Project changelog** (`docs: add project changelog`)
- `CHANGELOG.md` — created at repo root; `[Unreleased]` covers security sprint + CI + Docker SHA tagging; `[0.1.0]` covers Phase 0 Foundation (migrations 0001–0016, all capabilities)
- `README.md` — `CHANGELOG.md` row added to Documentation table
- ADR-021, RISK-018 documented

**Docker image Git SHA tagging** (`build: add docker image git sha tagging`)
- `docker-compose.yml` — `image: ghcr.io/your-org/nct-backend:${GIT_SHA:-latest}` added to `backend`; `image: ghcr.io/your-org/nct-backend:${GIT_SHA:-latest}` added to `worker` (removed redundant `build:`); `image: ghcr.io/your-org/nct-frontend:${GIT_SHA:-latest}` added to `frontend`
- `Makefile` — `GIT_SHA ?= $(shell git rev-parse --short HEAD)` at top; `build`, `deploy`, `rollback` targets added; `.PHONY` updated
- ADR-020, RISK-017 documented
- No registry login, no image push, no CI/CD pipeline — pattern only

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

- **319 passed, 4 skipped** as of 2026-06-09 (CORS localhost guard)
- No known failures or skips
- Warning: `passlib` uses deprecated `crypt` module (Python 3.12); no functional impact

## Active Risks

See `planning/RISKS.md` — RISK-002 (key loss), RISK-003 (terraform apply), RISK-006 (CSP unsafe-inline), RISK-009 (IAM role misconfiguration), RISK-010 (prompt truncation), RISK-011 (evaluator structural only), RISK-012 (alembic workdir), RISK-013 (root terraform-catalog refs), RISK-014 (OCI Vault not yet validated e2e), RISK-015 (CI basic quality only), RISK-016 (CORS domain change), RISK-017 (image tagging enables rollback only after CI/CD publishes tags), RISK-018 (changelog reconstructed from repo state), and RISK-019 (pending analyses stuck if Celery/Redis unavailable) are tracked.
