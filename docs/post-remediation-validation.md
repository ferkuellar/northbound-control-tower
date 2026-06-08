# Post-Remediation Validation

Phase G validates whether an applied remediation actually corrected the original finding.

An apply success is not enough to mark a finding resolved. Northbound must run a read-only rescan, refresh inventory, rerun the findings engine, compare before/after state, and generate evidence.

## Flow

1. Request reaches `APPLY_SUCCEEDED` or `OUTPUTS_CAPTURED`.
2. Operator runs `nb validate request <request_id>`.
3. Northbound captures before snapshots.
4. Collectors run in read-only mode.
5. Inventory is updated.
6. Findings are recalculated.
7. The original finding is diffed against latest findings.
8. Northbound records `RESOLVED`, `PARTIALLY_RESOLVED`, `STILL_OPEN`, or `VALIDATION_FAILED`.
9. A final remediation report is generated.

## Results

- `RESOLVED`: the original finding did not reappear in the validation run.
- `PARTIALLY_RESOLVED`: severity or evidence improved but risk remains.
- `STILL_OPEN`: the same rule/resource remains active.
- `VALIDATION_FAILED`: collector, credentials, API, timeout, or insufficient data prevented confirmation.

## Evidence

- `post-validation-result.json`
- `post-validation-result.md`
- `findings-before.json`
- `findings-after.json`
- `findings-diff.json`
- `rescan.log`
- `rescan-inventory-snapshot.json`
- `collector-run-metadata.json`
- `remediation-final-report.md`
- `remediation-final-report.json`

## Limitations

Phase G uses the existing inventory and findings engine synchronously for MVP. Celery can wrap the same service later without changing the validation model.
