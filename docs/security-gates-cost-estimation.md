# Security Gates and Cost Estimation

Phase D adds a controlled review layer between Terraform plan generation and any future approval workflow.

## Objective

Northbound can now analyze a Terraform plan for security, cost, destructive change risk, and policy gate readiness. It still cannot modify cloud infrastructure.

## Flow

1. `nb fix plan <finding_id>` creates a provisioning request.
2. `nb terraform validate <request_id>` prepares and validates the workspace.
3. `nb terraform plan <request_id>` creates `plan.out`, `plan.json`, and `plan.log`.
4. `nb security scan <request_id>` runs Checkov and stores `checkov.json` plus `checkov.log`.
5. `nb cost estimate <request_id>` runs Infracost and stores `infracost.json` plus `infracost.log`.
6. `nb risk summary <request_id>` creates `risk-summary.json` and `risk-summary.md`.
7. `nb gates evaluate <request_id>` writes `gates-result.json` and sets `READY_FOR_APPROVAL` or `GATES_BLOCKED`.

## Checkov

Checkov scans the Terraform workspace for security misconfigurations. Findings are parsed into pass/fail counts, failed checks, highest severity, and blocking finding count.

## Infracost

Infracost estimates monthly cost when the CLI and API key are available. If cost data is unavailable in local development, the result is stored as a warning instead of inventing a number.

## Policy Gates

Policy gates verify that a plan exists, the request is active, Checkov has no critical or blocking findings, cost evidence is present or explicitly unavailable, destructive changes are absent, and apply remains disabled.

## Risk Summary

The risk summary consolidates plan counts, destructive changes, security findings, cost data, template risk, approval requirement, and a human-readable recommendation.

## What Phase D Does

- Executes allowlisted Checkov and Infracost commands.
- Stores auditable security, cost, risk, and gate artifacts.
- Blocks critical security and destructive change conditions.
- Marks eligible requests as `READY_FOR_APPROVAL`.

## What Phase D Does Not Do

- No `terraform apply`.
- No `terraform destroy`.
- No approval workflow.
- No cloud changes.
- No auto-remediation.
- No arbitrary shell.

## Why Apply Is Still Disabled

Apply requires human approval, evidence review, audit metadata, and stricter production controls. Those belong to Phase E and later.
