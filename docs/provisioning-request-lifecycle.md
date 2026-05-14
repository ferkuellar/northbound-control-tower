# Provisioning Request Lifecycle

## Current Lifecycle

```text
DRAFT
READY_FOR_PLAN
PLAN_READY
SECURITY_SCAN_PASSED
COST_ESTIMATE_READY
RISK_SUMMARY_READY
GATES_PASSED
READY_FOR_APPROVAL
PENDING_APPROVAL
APPROVED
REJECTED
```

## Blocking And Failure States

```text
VALIDATION_FAILED
PLAN_FAILED
SECURITY_SCAN_FAILED
SECURITY_SCAN_BLOCKED
COST_ESTIMATE_FAILED
GATES_FAILED
GATES_BLOCKED
CANCELLED
APPROVAL_EXPIRED
```

## Future Lifecycle

Phase F and Phase G should add:

```text
APPLY_RUNNING
APPLY_SUCCEEDED
APPLY_FAILED
POST_VALIDATION_RUNNING
RESOLVED
```

## Notes

Approval is a change-control decision. It does not apply infrastructure. Controlled apply must validate the approved plan checksum before execution.
