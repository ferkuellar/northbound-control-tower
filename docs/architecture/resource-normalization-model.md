# Resource Normalization Model

## Purpose

The Resource Normalization Engine converts provider-specific AWS and OCI inventory outputs into one cloud-agnostic resource model. Downstream modules should consume normalized resources only and should not need to understand AWS or OCI response formats.

Supported downstream use cases:
- Inventory
- Findings
- Risk scoring
- Reporting
- Future AI analysis

## Normalized Schema

Core fields:
- `provider`: `aws` or `oci`
- `resource_category`: provider-neutral category
- `resource_id`: original provider resource identifier
- `raw_type`: original provider type, for traceability
- `name`: human-readable name, falling back to `resource_id`
- `region`: cloud region, or `global` for global resources

Standard optional fields:
- `account_id`
- `compartment_id`
- `tenant_id`
- `cloud_account_id`
- `availability_zone`
- `availability_domain`
- `lifecycle_status`
- `exposure_level`
- `environment`
- `criticality`
- `owner`
- `cost_center`
- `application`
- `service_name`
- `tags`
- `metadata`
- `relationships`
- `discovered_at`
- `fingerprint`

## Provider Mappings

AWS:
- EC2 Instance -> `compute`
- EBS Volume -> `block_storage`
- S3 Bucket -> `object_storage`
- RDS DB Instance -> `database`
- IAM User/Role/Policy -> `identity`
- VPC/Subnet/Security Group -> `network`
- CloudWatch Alarm -> `monitoring`

OCI:
- Compute Instance -> `compute`
- Boot Volume / Block Volume -> `block_storage`
- VCN/Subnet/Security List/NSG -> `network`
- Load Balancer -> `network`
- Compartment -> `identity`
- User/Group/Policy -> `identity`
- Monitoring Alarm -> `monitoring`

Unknown or malformed resources are persisted as:
- `resource_category=unknown`
- `lifecycle_status=unknown`

## Tag Standards

AWS tags are normalized from:

```json
[
  {"Key": "env", "Value": "prod"}
]
```

to:

```json
{
  "env": "prod"
}
```

OCI tags preserve freeform and defined tags:

```json
{
  "freeform": {},
  "defined": {},
  "flat": {}
}
```

The engine derives standard ownership fields from common tag keys:
- `env`
- `environment`
- `owner`
- `costcenter`
- `cost_center`
- `app`
- `application`
- `service`
- `criticality`

## Metadata Standards

Standard metadata keys are used when available:
- `cpu_count`
- `memory_gb`
- `shape`
- `instance_type`
- `storage_gb`
- `engine`
- `version`
- `public_ip`
- `private_ip`
- `vpc_id`
- `vcn_id`
- `subnet_id`
- `security_groups`
- `nsgs`
- `attached_to`
- `alarm_state`
- `created_time`
- `updated_time`

Provider-specific fields are preserved under:

```json
{
  "provider_details": {}
}
```

Credential-like keys are stripped from metadata.

## Upsert Strategy

Each normalized resource gets a deterministic fingerprint:

```text
provider + cloud_account_id + region + resource_id + raw_type
```

Upsert rule:
- Same `tenant_id + cloud_account_id + fingerprint` updates an existing resource.
- New fingerprint inserts a new resource.
- `created_at` is preserved.
- `discovered_at` is updated on every scan.

A fallback legacy lookup by `tenant_id + cloud_account_id + provider + resource_id` remains for resources created before Phase 5.

## Known Limitations

- Scans remain synchronous in Phase 5.
- Provider-specific relationship extraction is minimal.
- Exposure level inference is conservative and based on metadata signals.
- Some existing resources will receive fingerprints only after being rediscovered.
- OCI/AWS collection depth depends on permissions available to the configured account.
