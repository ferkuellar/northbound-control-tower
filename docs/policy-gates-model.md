# Policy Gates Model

## Gates

Phase D evaluates:

- Terraform plan exists.
- Request reached a post-plan status.
- Security scan evidence exists.
- No critical security findings.
- No blocked high-risk findings.
- Cost estimate exists or is explicitly unavailable with a warning.
- Terraform plan has no delete or replace actions.
- Request is not cancelled.
- Execution template is enabled.
- Terraform apply remains disabled.

## Results

Gate result values:

- `PASS`
- `WARN`
- `FAIL`
- `BLOCKED`

## READY_FOR_APPROVAL

A request becomes `READY_FOR_APPROVAL` when there are no failed or blocked gates. Warnings, such as Infracost being unavailable in a local environment, are allowed.

## GATES_BLOCKED

A request becomes `GATES_BLOCKED` when a gate detects destructive changes, critical security findings, cancelled state, missing plan evidence, or a disabled template.

## Phase E

Phase E should add human approval records, approver identity, timestamps, notes, and rejection paths. Apply remains disabled until a later phase.
