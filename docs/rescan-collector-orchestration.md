# Rescan Collector Orchestration

Phase G uses existing AWS and OCI inventory collectors in read-only mode.

## Trigger Sources

- `MANUAL`
- `POST_REMEDIATION_VALIDATION`
- `SCHEDULED` for future use

## CollectorRun

Each rescan records a `CollectorRun` with provider, account, region, status, resource count, findings count, error message, duration, and metadata.

## Error Handling

Collector failure does not mark a finding resolved. If inventory or findings recalculation fails, validation result becomes `VALIDATION_FAILED`.

## Read-Only Principle

No Terraform, AWS write CLI, OCI write action, or shell command is used during validation. Collectors query cloud APIs and update Northbound inventory only.
