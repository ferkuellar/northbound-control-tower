# Admin Client Experience

## Purpose

Northbound Control Tower now presents a client-oriented administration flow instead of only a static dashboard. ADMIN users can register tenants, select the active client context, seed the Clara Fintech AWS FinOps case study, and open report/export actions from operational views.

## Tenant / Client Context Model

- The frontend exposes a visible client selector in the executive dashboard.
- ADMIN users can request `/api/v1/dashboard/executive?tenant_id=...`.
- ANALYST and VIEWER users remain constrained to their JWT tenant.
- Admin client management is exposed through `/api/v1/admin/tenants`.

Tenant metadata added:

- `industry`
- `contact_name`
- `contact_email`
- `notes`

## Cloud Account Context Model

The dashboard includes a cloud account selector populated from the selected tenant dashboard response. The selected scope is shown in the top bar as client, cloud account, provider, and last collection time.

## Report Action Flow

Report actions are visible in the dashboard and cost optimization view:

- Generate Executive Report
- Generate Technical Report
- Preview Latest
- Download PDF
- Print

Report generation accepts an optional `tenant_id`; only ADMIN can generate for a tenant different from the JWT tenant.

## Clara Case Study Seed Data

The dev/admin seed endpoint is:

`POST /api/v1/cost-optimization/demo/clara`

It creates:

- Tenant: Clara Fintech
- AWS Production cloud account
- Cost optimization case with 250000 USD monthly spend
- Service breakdown: EC2, EBS, RDS, S3, EKS, Lambda
- Normalized summary resources
- Deterministic findings
- Deterministic scores
- Prioritized recommendations

## Cost Optimization Assumptions

Savings are estimates for test data only:

- EC2 rightsizing/Savings Plans: 20% of EC2 spend
- EBS cleanup: 15% of EBS spend
- S3 lifecycle: 25% of S3 spend
- EKS rightsizing: 15% of EKS spend
- Snapshot retention: 5% of EBS spend

The UI labels all impact as estimated and requires validation before destructive cleanup.

## Security Considerations

- All new endpoints require JWT.
- ADMIN permission is required for tenant creation/update and Clara seed.
- Non-admin users cannot switch to another tenant.
- CSV export checks tenant scope.
- Cloud credentials are not exposed.
- Report tenant override is permission-controlled.

## Future Improvements

- Persist user-selected client context server-side.
- Add first-class tenant membership for cross-tenant analyst access.
- Add report preview/download through authenticated blob fetch in all browsers.
- Add diagram export after a dedicated diagram renderer is selected.
