# Project State

_Last updated: 2026-06-09_

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

- **216 passed, 1 skipped** as of 2026-06-09
- No known failures or skips
- Warning: `passlib` uses deprecated `crypt` module (Python 3.12); no functional impact

## Active Risks

See `planning/RISKS.md` — RISK-002 (key loss), RISK-003 (terraform apply), and RISK-006 (CSP unsafe-inline) are tracked open.
