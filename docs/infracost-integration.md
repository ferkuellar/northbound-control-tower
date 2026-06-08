# Infracost Integration

## Command

Northbound runs Infracost with:

```bash
infracost breakdown --path <workspace_path> --format json --out-file infracost.json
```

The command is allowlisted, executed without `shell=True`, and scoped to the validated Terraform workspace.

## Requirements

- Infracost CLI installed in the backend or worker image.
- `INFRACOST_API_KEY` configured.

## Missing API Key

If the API key is missing, Phase D stores an unavailable cost estimate and returns an actionable warning. It does not invent costs.

## Extracted Data

- currency
- total monthly cost
- total hourly cost
- past monthly cost
- monthly diff
- projects count
- resources count
- unsupported resource count
- resource cost entries

## Unsupported Resources

Unsupported resources are counted when present. Missing or unsupported cost data remains unavailable rather than estimated.

## Artifacts

- `infracost.json`
- `infracost.log`
