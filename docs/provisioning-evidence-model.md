# Provisioning Evidence Model

Provisioning evidence records the artifacts generated while turning a finding into a governed Terraform plan.

## Artifact Types

- `REQUEST_INPUT`
- `TFVARS`
- `EVIDENCE`
- `TERRAFORM_INIT_LOG`
- `TERRAFORM_VALIDATE_LOG`
- `TERRAFORM_PLAN_LOG`
- `TERRAFORM_PLAN_BINARY`
- `TERRAFORM_PLAN_JSON`
- `TERRAFORM_WORKSPACE_METADATA`

## Storage

In local development, files are stored in:

```text
runtime/terraform-workspaces/<request_code>/
```

The database stores metadata only: file name, local path, content type, size, checksum, creator and timestamps. PDF, binary plan files and large logs are not stored as raw blobs in the database.

## Audit Relationship

Cloud Shell command audits capture who executed `nb terraform validate`, `nb terraform plan` and `nb evidence show`. Provisioning artifacts capture what evidence was produced by those commands.

## Future Storage

Future phases should move file artifacts to S3-compatible object storage or a tenant-aware artifact service. The current model already separates artifact metadata from file storage to support that migration.
