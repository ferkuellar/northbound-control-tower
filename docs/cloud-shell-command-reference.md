# Cloud Shell Command Reference

| Command | Description | Required role | Risk | Enabled | Example |
| --- | --- | --- | --- | --- | --- |
| `nb help` | Show available commands | VIEWER | LOW | Yes | `nb help` |
| `nb status` | Show shell subsystem status | VIEWER | LOW | Yes | `nb status` |
| `nb findings list` | List findings for current tenant | VIEWER | LOW | Yes | `nb findings list --severity high` |
| `nb findings show <finding_id>` | Show finding details | VIEWER | LOW | Yes | `nb findings show FIND-001` |
| `nb fix suggest <finding_id>` | Suggest safe remediation approach | OPERATOR | MEDIUM | Yes | `nb fix suggest FIND-001` |
| `nb fix plan <finding_id>` | Create persisted draft request | OPERATOR | MEDIUM | Yes | `nb fix plan FIND-001` |
| `nb templates list` | List provisioning templates | OPERATOR | LOW | Yes | `nb templates list` |
| `nb templates show <template_id>` | Show template metadata | OPERATOR | LOW | Yes | `nb templates show local-noop-validation` |
| `nb requests list` | List persisted requests | OPERATOR | LOW | Yes | `nb requests list` |
| `nb requests show <request_id>` | Show persisted request | OPERATOR | LOW | Yes | `nb requests show REQ-1001` |
| `nb evidence show <request_id>` | Show request evidence and artifacts | VIEWER | LOW | Yes | `nb evidence show REQ-1001` |
| `nb terraform validate <request_id>` | Prepare workspace, run Terraform init and validate | OPERATOR | HIGH | Yes | `nb terraform validate REQ-1001` |
| `nb terraform plan <request_id>` | Run Terraform plan and convert plan to JSON | OPERATOR | HIGH | Yes | `nb terraform plan REQ-1001` |
| `nb security scan <request_id>` | Run Checkov scan against the Terraform workspace | OPERATOR | HIGH | Yes | `nb security scan REQ-1001` |
| `nb cost estimate <request_id>` | Run Infracost estimate for the Terraform workspace | OPERATOR | MEDIUM | Yes | `nb cost estimate REQ-1001` |
| `nb risk summary <request_id>` | Generate JSON and Markdown risk summary | OPERATOR | MEDIUM | Yes | `nb risk summary REQ-1001` |
| `nb gates evaluate <request_id>` | Evaluate policy gates and set gate decision | OPERATOR | HIGH | Yes | `nb gates evaluate REQ-1001` |
| `nb approvals list` | List provisioning requests waiting for approval | APPROVER | LOW | Yes | `nb approvals list` |
| `nb approvals show <request_id>` | Show approval detail for a request | APPROVER | LOW | Yes | `nb approvals show REQ-1001` |
| `nb approve <request_id> --note "..."` | Approve a request after review | APPROVER | HIGH | Yes | `nb approve REQ-1001 --note "Reviewed security, cost and gates"` |
| `nb reject <request_id> --note "..."` | Reject a request with reason | APPROVER | HIGH | Yes | `nb reject REQ-1001 --note "Cost too high"` |
| `nb terraform apply <request_id>` | Apply the approved immutable Terraform plan | OPERATOR | CRITICAL | Yes | `nb terraform apply REQ-1001` |
| `nb outputs show <request_id>` | Show captured Terraform outputs with sensitive values redacted | VIEWER | LOW | Yes | `nb outputs show REQ-1001` |
| `nb validate request <request_id>` | Run post-remediation validation after apply | OPERATOR | HIGH | Yes | `nb validate request REQ-1001` |
| `nb validate finding <finding_id>` | Run post-remediation validation for the applied request tied to a finding | OPERATOR | HIGH | Yes | `nb validate finding FIND-001` |
| `nb rescan account <account_id>` | Run read-only collector rescan for a cloud account | OPERATOR | MEDIUM | Yes | `nb rescan account AWS-PROD-001` |
| `nb remediation report <request_id>` | Show final remediation report | VIEWER | LOW | Yes | `nb remediation report REQ-1001` |
| `nb terraform destroy <request_id>` | Destructive Terraform command | N/A | CRITICAL | Blocked | `nb terraform destroy REQ-1001` |

## Terraform Validate Output

```text
Terraform validation completed for REQ-1001.

Workspace:
runtime/terraform-workspaces/REQ-1001

Steps:
- workspace prepared: OK
- terraform init: OK
- terraform validate: OK

Status:
TERRAFORM_VALIDATE_SUCCEEDED
```

## Terraform Apply Blocked Output

```text
Apply blocked for REQ-1001.

Reason:
Request status must be APPROVED, current status is READY_FOR_APPROVAL

No infrastructure changes were executed.
```

## Terraform Destroy Blocked Output

```text
Command blocked. Terraform destroy is not available from Northbound Cloud Shell.
```

## Phase D Command Flow

```text
nb terraform plan REQ-1001
nb security scan REQ-1001
nb cost estimate REQ-1001
nb risk summary REQ-1001
nb gates evaluate REQ-1001
nb approvals list
nb approvals show REQ-1001
nb approve REQ-1001 --note "Reviewed security, cost and gates"
nb terraform apply REQ-1001
nb outputs show REQ-1001
nb validate request REQ-1001
nb remediation report REQ-1001
nb evidence show REQ-1001
```
