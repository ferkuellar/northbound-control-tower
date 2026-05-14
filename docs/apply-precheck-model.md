# Apply Precheck Model

## Purpose

Prechecks prevent Northbound from applying a stale, modified, rejected, blocked, or unsafe Terraform plan.

## Rules

- Request must be `APPROVED`.
- Approval record must exist and be `APPROVED`.
- Approval must not be expired.
- Required artifacts must exist.
- Approved checksums must match current files.
- Gates must not be blocked.
- Plan must not include delete or replace actions.
- Workspace must live under the managed Terraform runtime directory.
- Apply lock must be available.

## Checksum Verification

Phase F verifies:

- `plan.out`
- `plan.json`
- `risk-summary.json`
- `gates-result.json`

Any mismatch blocks apply and writes `apply-precheck-result.json`.

## Error Handling

Failed prechecks set `APPLY_PRECHECK_FAILED`. No Terraform command is executed.
