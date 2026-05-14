# Provisioning Console Roadmap

## Phase A — Cloud Shell Foundation

Implemented foundation:

- xterm.js terminal
- WebSocket backend
- command parser
- command registry
- RBAC authorization
- command audit table
- safe command responses
- disabled Terraform placeholders

## Phase B — Provisioning Request Workflow

Objective:

- Persist real `ProvisioningRequest`.
- Associate request with `Finding`.
- Create initial Terraform template catalog.
- Generate validated request inputs.
- Prepare isolated workspace.
- Continue blocking Terraform execution.

Status: implemented as foundation. Requests and JSON artifacts are persisted; Terraform workspace creation remains future work.

## Phase C — Terraform Validate/Plan

Objective:

- Execute `terraform init`.
- Execute `terraform validate`.
- Execute `terraform plan -out=plan.out`.
- Convert plan to JSON.
- Store plan artifacts.
- Show plan summary in Cloud Shell.
- Keep `apply` disabled.

## Phase D — Security Gates + Cost Estimation

Objective:

- Run Checkov or equivalent IaC checks.
- Run Infracost estimate where configured.
- Block high-risk plans.
- Attach gate evidence to the request.

## Phase E — Approval Workflow

Objective:

- Add approver role workflow.
- Require explicit approval.
- Track approver, timestamp, plan checksum and decision.

## Phase F — Controlled Apply

Objective:

- Execute apply only against approved immutable plan.
- Never allow `apply -auto-approve`.
- Stream logs safely.
- Persist artifacts.

## Phase G — Post-Remediation Validation

Objective:

- Trigger collector rescan.
- Re-run deterministic findings.
- Validate finding closure or status change.
- Capture evidence.

## Phase H — Evidence and Executive Reports

Objective:

- Link remediation evidence to reports.
- Include before/after score impact.
- Add executive and technical remediation appendix.
