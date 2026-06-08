# Checkov Integration

## Command

Northbound runs Checkov with:

```bash
checkov -d <workspace_path> -o json
```

The command is executed with `subprocess.run` using an argument list, `shell=True` is not used, and the working directory is the validated Terraform workspace.

## Output

Artifacts:

- `checkov.json`
- `checkov.log`

## Exit Codes

Checkov can return a non-zero exit code when it detects policy failures. Phase D treats JSON output as scan evidence and uses parsed findings, not the exit code alone, to decide whether the request is blocked.

## Findings

The parser extracts:

- passed checks
- failed checks
- skipped checks
- failed check metadata
- highest severity
- blocking finding count

## Severity Limitations

Some Checkov outputs do not include severity. Northbound maps obvious critical and high-risk phrases conservatively, otherwise severity remains `UNKNOWN`.

## Blocking

Critical findings and high-risk blocking findings prevent a request from reaching `READY_FOR_APPROVAL`.

## Evidence

Logs are sanitized before storage. The workspace path is validated so Checkov only runs inside the managed Terraform runtime directory.
