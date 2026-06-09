# Project State

_Last updated: 2026-06-08_

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

- **159 passed** as of 2026-06-08
- No known failures or skips
- Warning: `passlib` uses deprecated `crypt` module (Python 3.12); no functional impact

## Active Risks

See `planning/RISKS.md` — RISK-002 (key loss) and RISK-003 (terraform apply) are tracked open.
