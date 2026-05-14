# Approval Security Model

## RBAC

Only `APPROVER`, `ADMIN`, or higher-ranked roles can approve or reject requests. `VIEWER` and `OPERATOR` cannot approve.

## Blocked Gates

Requests with `GATES_BLOCKED`, blocked gate evidence, destructive changes, or critical security findings cannot be approved.

## Required Artifacts

Approval requires:

- Terraform plan JSON artifact
- Risk summary artifact
- Gates result artifact

## Production Approval Design

If the environment is `prod` or `production`, approval records are marked `requires_double_approval = true` and `approval_level = PRODUCTION`. Full two-person approval enforcement is intentionally left for a follow-up hardening phase.

## Requester and Approver Separation

The model stores `requested_by` and `approved_by`. Phase E prepares the data model for separation-of-duty enforcement; production-grade final enforcement should be completed before controlled apply.

## Immutable Snapshots

Approval records store snapshots of:

- risk summary
- gates result
- cost estimate
- security scan
- plan summary

## Checksums

Approval records store checksums for approved `plan.out`, `plan.json`, `risk-summary.json`, and `gates-result.json` when available.

## Apply Prohibition

Phase E does not run `terraform apply`, `terraform destroy`, AWS CLI, or arbitrary shell commands.
