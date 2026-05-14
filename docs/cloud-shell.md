# Northbound Cloud Shell

## Purpose

Northbound Cloud Shell is a controlled operations console for investigating findings, preparing remediation plans, and preserving command evidence inside NORTHBOUND CONTROL TOWER.

It intentionally looks like a terminal, but it is not a Linux shell. It executes only registered `nb` commands through a backend Command Registry.

## Why It Is Not A Free Terminal

The console does not connect to `/bin/bash`, `sh`, PowerShell, AWS CLI, OCI CLI, or Terraform directly. This prevents operators from bypassing RBAC, tenant isolation, approvals, audit logging, and evidence capture.

Blocked examples:

- `bash`
- `sh`
- `zsh`
- `powershell`
- `cat .env`
- `printenv`
- `terraform destroy`
- `terraform apply -auto-approve`
- `aws s3 rm`

## Architecture

```text
Next.js /cloud-shell
→ xterm.js terminal
→ WebSocket /ws/cloud-shell
→ CloudShellExecutor facade
→ CommandParser
→ CommandRegistry
→ Authorization
→ Command Strategy
→ CloudShellCommandAudit
→ Structured response
```

## WebSocket Flow

1. Frontend opens `/ws/cloud-shell`.
2. JWT is sent via WebSocket subprotocol, not printed in the terminal.
3. Backend authenticates the user and tenant.
4. Backend sends a welcome banner.
5. User enters an `nb` command.
6. Backend executes only registered commands.
7. Backend returns structured JSON or text output.
8. Every command is written to `cloud_shell_command_audits`.

## Command Registry

The registry is the allowlist. A command must be present in the registry before it can execute.

Implemented commands:

- `nb help`
- `nb status`
- `nb findings list`
- `nb findings show <finding_id>`
- `nb fix suggest <finding_id>`
- `nb fix plan <finding_id>`
- `nb requests list`
- `nb requests show <request_id>`
- `nb evidence show <request_id>`

Recognized but disabled:

- `nb terraform validate <request_id>`
- `nb terraform plan <request_id>`
- `nb terraform apply <request_id>`
- `nb approve <request_id>`
- `nb validate <finding_id>`

## Audit

Each command persists:

- user
- tenant
- raw command
- parsed command name
- arguments
- status
- risk level
- approval requirement
- stdout/stderr fields
- timing
- source IP
- user agent

No secrets, tokens, `.env` values, cloud credentials, private keys, or raw provider payloads should be written to command output.

## Design Patterns Applied

- Facade: `CloudShellExecutor`
- Singleton/Registry: `CommandRegistry`
- Strategy: command handler classes
- Factory-like composition: `build_default_registry`
- Builder: `ShellResponseBuilder`
- Adapter: `FindingShellAdapter`
- Decorator concept: authorization/audit wrappers are explicit in the executor for async clarity
- Observer: deferred; audit is direct for this foundation to avoid premature event architecture

## Roadmap

The next phase should persist real `ProvisioningRequest` records and associate them with findings. Terraform should remain disabled until request workflow, approvals, security gates, artifact storage, and evidence validation exist.

