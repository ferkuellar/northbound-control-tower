# Change Control Model

Northbound models operational change as an evidence-backed lifecycle.

## Request

The provisioning request links the finding, tenant, provider, template, requester, risk level, and current status.

## Plan

Terraform validation and planning produce `plan.out`, `plan.json`, and `plan.log`. Phase E requires the plan JSON artifact before approval.

## Security Scan

Checkov evidence is stored as `checkov.json` and `checkov.log`. Critical or blocking findings prevent approval.

## Cost Estimate

Infracost evidence is stored as `infracost.json` and `infracost.log`. Missing local cost data may be a warning, not an invented value.

## Gates

Policy gates decide whether the request can move to approval. Blocked gates prevent approval.

## Approval

Approval records store decision, approver, timestamp, notes, snapshots, and checksums of reviewed artifacts.

## Future Apply

Phase F should apply only the approved `plan.out` after validating checksums.

## Evidence

Every phase writes artifacts so a reviewer can reconstruct what happened.

## Future Post-Validation

Phase G should rescan cloud state and verify whether the original finding was resolved.
