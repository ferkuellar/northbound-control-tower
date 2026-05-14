# Provisioning Request Workflow

## Purpose

Phase B turns `nb fix plan <finding_id>` from an in-memory stub into a persistent provisioning request draft. It still does not execute Terraform.

## Flow

```text
Finding
→ nb fix plan <finding_id>
→ Template Catalog
→ ProvisioningRequest
→ Request artifacts
→ Evidence available through Cloud Shell and API
```

## Persisted Objects

### ProvisioningRequest

Stores:

- tenant
- cloud account
- finding
- requester
- provider
- template key/version
- status
- risk level
- input variables
- generated `tfvars_json`
- evidence
- approval requirement

### ProvisioningArtifact

Stores Phase B artifacts:

- `request-input.json`
- `terraform.tfvars.json`
- `phase-b-evidence.json`

Artifacts are JSON records in PostgreSQL for this phase. Filesystem/object-storage artifacts are future work.

## Template Catalog

The initial catalog is code-based:

- `cloud-public-exposure-review`
- `cloud-volume-snapshot-and-cleanup`
- `cloud-tagging-governance`
- `cloud-monitoring-baseline`

Unknown finding types receive a generic provider/finding template key. This keeps the shell useful without introducing unsafe Terraform execution.

## API

Endpoints:

- `GET /api/v1/provisioning/templates`
- `POST /api/v1/provisioning/requests/from-finding`
- `GET /api/v1/provisioning/requests`
- `GET /api/v1/provisioning/requests/{request_id}`
- `GET /api/v1/provisioning/requests/{request_id}/artifacts`

Authorization:

- Read endpoints use findings read permission.
- Creating requests from findings uses findings write permission.

## Cloud Shell Integration

Updated commands:

- `nb fix plan <finding_id>` persists a draft request.
- `nb requests list` reads persisted tenant requests.
- `nb requests show <request_id>` reads persisted request metadata.
- `nb evidence show <request_id>` lists stored request artifacts.

## Security

Phase B keeps these controls:

- No Terraform execution.
- No cloud API calls.
- No destructive operations.
- Tenant isolation on every query.
- No credentials in artifacts.
- Approval status is recorded but no approval workflow is active yet.

## Limitations

- Request numbering is database-count based for local MVP.
- Artifacts are JSON DB records, not object storage files.
- Template catalog is code-based, not database-managed.
- No Terraform workspace is created yet.
- No validate/plan/apply execution exists.

