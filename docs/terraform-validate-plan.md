# Terraform Validate and Plan

Phase C adds controlled Terraform validation and planning to Northbound Cloud Shell. It converts a persisted `ProvisioningRequest` into an isolated Terraform workspace with auditable logs, `plan.out`, `plan.json` and evidence metadata.

## What This Phase Does

- Prepares `runtime/terraform-workspaces/<request_code>/`.
- Generates `terraform.tfvars.json` from sanitized request data.
- Copies an approved Terraform template into the workspace.
- Runs only:
  - `terraform init -input=false -no-color`
  - `terraform validate -no-color`
  - `terraform plan -out=plan.out -input=false -no-color`
  - `terraform show -json plan.out`
- Stores artifact metadata and checksums.
- Updates `ProvisioningRequest.status`.
- Exposes evidence through `nb evidence show <request_id>`.

## What This Phase Does Not Do

- No `terraform apply`.
- No `terraform destroy`.
- No approval workflow.
- No Checkov.
- No Infracost.
- No cloud API calls.

## Safe Template Strategy

The default Phase C execution template is `local-noop-validation`. It uses local Terraform behavior and does not configure AWS, OCI or any other cloud provider. Existing remediation templates remain disabled for Terraform execution until later phases.

## State Flow

```text
DRAFT
-> TERRAFORM_INIT_RUNNING
-> TERRAFORM_INIT_SUCCEEDED
-> TERRAFORM_VALIDATE_RUNNING
-> TERRAFORM_VALIDATE_SUCCEEDED
-> PLAN_RUNNING
-> PLAN_READY
```

Failure states include `TERRAFORM_INIT_FAILED`, `TERRAFORM_VALIDATE_FAILED` and `PLAN_FAILED`.

## Phase D Preparation

The generated `plan.json` is parsed into counts for add, change, delete, replace and no-op actions. That summary is intentionally ready for future security gates, cost estimation and approval workflow.
