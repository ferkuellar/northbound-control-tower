# Approval Workflow

Phase E adds formal human approval for provisioning requests that already passed Terraform planning, security scan, cost estimation, risk summary, and policy gates.

## Objective

Approval records capture who reviewed the change, when the decision happened, what note was provided, and which risk, cost, security, gates, and plan snapshots were reviewed.

## Flow

1. `nb gates evaluate <request_id>` marks an eligible request `READY_FOR_APPROVAL`.
2. `nb approvals list` creates or lists pending approval records.
3. `nb approvals show <request_id>` displays the review packet.
4. `nb approve <request_id> --note "..."` records approval and marks the request `APPROVED`.
5. `nb reject <request_id> --note "..."` records rejection and marks the request `REJECTED`.

## States

- `READY_FOR_APPROVAL`
- `PENDING_APPROVAL`
- `APPROVED`
- `REJECTED`
- `APPROVAL_EXPIRED`

## What Can Be Approved

A request can be approved only when it is active, in `READY_FOR_APPROVAL` or `PENDING_APPROVAL`, has plan/risk/gates artifacts, has no blocked gates, has no destructive changes, and has no critical security findings.

## What Is Rejected

Approvers and admins can reject non-terminal requests with a required note. Rejection blocks future apply for the request.

## Why There Is No Apply Yet

Apply belongs to Phase F. Phase E records the human decision and immutable snapshots, but does not execute Terraform or cloud commands.

## Commands

- `nb approvals list`
- `nb approvals show <request_id>`
- `nb approve <request_id> --note "..."`
- `nb reject <request_id> --note "..."`
