# Controlled Terraform Apply

Phase F is the first phase that can modify infrastructure. It executes Terraform only against an approved immutable plan.

## Allowed Command

```bash
terraform apply -input=false -no-color plan.out
```

Northbound never regenerates the plan during apply.

## Prohibited Commands

- `terraform apply -auto-approve`
- `terraform apply` without `plan.out`
- `terraform destroy`
- `terraform force-unlock`
- `terraform import`
- `terraform state rm`
- `terraform state mv`
- arbitrary shell commands

## Flow

1. Request reaches `APPROVED`.
2. `nb terraform apply <request_id>` runs prechecks.
3. Checksums are compared against the approval snapshot.
4. An execution lock is acquired.
5. Terraform applies `plan.out`.
6. `apply.log` and `apply-metadata.json` are stored.
7. Terraform outputs are captured with `terraform output -json`.
8. `nb outputs show <request_id>` displays non-sensitive outputs.

## Execution Mode

The Phase F MVP executes apply synchronously through the backend service. The service boundary is intentionally narrow so a Celery task can wrap the same precheck, lock, apply, output, and evidence workflow later without changing the security model.

## Prechecks

- Request is `APPROVED`.
- Approval decision is `APPROVED`.
- Approval is not expired.
- `plan.out`, `plan.json`, `risk-summary.json`, and `gates-result.json` exist.
- Approved checksums match current files.
- Gates are not blocked.
- Plan has no destructive changes.
- Workspace path is valid.
- No active apply lock exists.

## Artifacts

- `apply-precheck-result.json`
- `apply.log`
- `apply-metadata.json`
- `outputs.json`

## Phase G

Phase G should validate whether the applied change actually remediated the finding.
