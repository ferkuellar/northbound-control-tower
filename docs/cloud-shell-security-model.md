# Cloud Shell Security Model

## Principle

Terminal visual, controlled commands, isolated execution path, human approval, evidence capture, and post-change validation.

## Threat Model

Primary risks:

- Arbitrary OS command execution
- Cloud credential exposure
- Tenant data leakage
- Unapproved infrastructure changes
- Terraform destructive actions
- AI-generated or automated remediation
- Missing audit evidence

## Command Boundary

Only `nb` commands are accepted. Non-`nb` commands are blocked before registry lookup.

Blocked categories:

- OS shells
- filesystem reads for secrets
- environment variable dumps
- cloud CLI commands
- destructive Terraform actions
- path traversal

## Allowlist

The Command Registry is the only allowlist. Unknown commands return a controlled error and do not execute external processes.

## RBAC

Current role mapping:

```text
VIEWER:
  nb help
  nb status
  nb findings list
  nb findings show
  nb evidence show

OPERATOR / ANALYST:
  VIEWER commands
  nb fix suggest
  nb fix plan
  nb requests list
  nb requests show

ADMIN:
  all enabled foundation commands
```

Future roles `APPROVER` and `BREAKGLASS_ADMIN` are recognized conceptually but do not unlock dangerous behavior in this phase.

## Terraform Controls

This phase does not execute Terraform.

Explicitly prohibited:

- `terraform destroy`
- `terraform apply -auto-approve`
- direct `terraform apply`
- Terraform without request, approval and evidence workflow

Recognized Terraform commands return `NOT_IMPLEMENTED`.

## Secret Protection

The shell must never output:

- JWT tokens
- `.env` values
- cloud access keys
- private keys
- provider API keys
- raw cloud payloads that may contain sensitive metadata

## Audit

Every command is written to `cloud_shell_command_audits`, including blocked and rejected commands. This makes operator behavior reviewable without allowing bypass of controls.

## Future Approval Model

Future controlled apply must require:

- persisted provisioning request
- Terraform plan artifact
- security scan
- cost estimate
- human approval
- post-remediation validation
- evidence attachment

