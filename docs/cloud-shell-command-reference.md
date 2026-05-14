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
| `nb terraform apply <request_id>` | Future controlled apply | OPERATOR | CRITICAL | No | `nb terraform apply REQ-1001` |
| `nb terraform destroy <request_id>` | Destructive Terraform command | N/A | CRITICAL | Blocked | `nb terraform destroy REQ-1001` |
| `nb approve <request_id>` | Future approval command | APPROVER | HIGH | No | `nb approve REQ-1001` |
| `nb validate <finding_id>` | Future post-remediation validation | OPERATOR | MEDIUM | No | `nb validate FIND-001` |

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

## Terraform Apply Disabled Output

```text
Command recognized but disabled in this phase.
Reason: Terraform apply requires approval workflow, security gates, cost review and controlled execution policy.
```

## Terraform Destroy Blocked Output

```text
Command blocked. Only Northbound controlled commands are allowed.
```
