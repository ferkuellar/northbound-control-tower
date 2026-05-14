# Terraform Output Handling

## Capture

After successful apply, Northbound runs:

```bash
terraform output -json
```

The command is executed without `shell=True`.

## Storage

Outputs are stored as `outputs.json` with artifact type `TERRAFORM_OUTPUT_JSON`.

## Console Display

`nb outputs show <request_id>` renders a table. Outputs marked `sensitive: true` are displayed as `[SENSITIVE]`.

## Safety

Northbound does not dump raw output JSON to the Cloud Shell. Sensitive values stay redacted in the console.
