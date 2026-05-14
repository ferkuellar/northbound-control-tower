# Cloud Shell Command Reference

| Command | Description | Required role | Risk | Enabled | Example |
| --- | --- | --- | --- | --- | --- |
| `nb help` | Show available commands | VIEWER | LOW | Yes | `nb help` |
| `nb status` | Show shell subsystem status | VIEWER | LOW | Yes | `nb status` |
| `nb findings list` | List findings for current tenant | VIEWER | LOW | Yes | `nb findings list --severity high` |
| `nb findings show <finding_id>` | Show finding details | VIEWER | LOW | Yes | `nb findings show FIND-001` |
| `nb fix suggest <finding_id>` | Suggest safe remediation approach | OPERATOR | MEDIUM | Yes | `nb fix suggest FIND-001` |
| `nb fix plan <finding_id>` | Create persisted draft request | OPERATOR | MEDIUM | Yes | `nb fix plan FIND-001` |
| `nb requests list` | List persisted draft requests | OPERATOR | LOW | Yes | `nb requests list` |
| `nb requests show <request_id>` | Show persisted request | OPERATOR | LOW | Yes | `nb requests show REQ-1001` |
| `nb evidence show <request_id>` | Show persisted request evidence | VIEWER | LOW | Yes | `nb evidence show REQ-1001` |
| `nb terraform validate <request_id>` | Future Terraform validation | APPROVER | HIGH | No | `nb terraform validate REQ-1001` |
| `nb terraform plan <request_id>` | Future Terraform plan | APPROVER | HIGH | No | `nb terraform plan REQ-1001` |
| `nb terraform apply <request_id>` | Future controlled apply | APPROVER | CRITICAL | No | `nb terraform apply REQ-1001` |
| `nb approve <request_id>` | Future approval command | APPROVER | HIGH | No | `nb approve REQ-1001` |
| `nb validate <finding_id>` | Future post-remediation validation | OPERATOR | MEDIUM | No | `nb validate FIND-001` |

## Expected Disabled Output

```text
Command recognized but not enabled in this phase.
Reason: Terraform execution requires provisioning workflow, approval model, security gates and evidence store.
```

## Expected Status Output

```text
Northbound Cloud Shell Status

API: OK
WebSocket: OK
Command Registry: OK
Audit Logger: OK
Terraform Runner: Disabled
Auto-remediation: Disabled
Mode: Controlled Command Shell
```
