# Apply Evidence Model

## Artifacts

`apply-precheck-result.json` records every precheck and failure reason.

`apply.log` stores sanitized Terraform stdout/stderr and exit code.

`apply-metadata.json` stores command label, timestamps, duration, exit code, success flag, and lock token.

`outputs.json` stores raw Terraform output JSON after sanitization.

## Checksums

Apply is tied to approval snapshot checksums. If any approved artifact changes, apply is blocked.

## Audit Relationship

Cloud Shell command audit records who invoked apply. Provisioning artifacts record what was executed and produced.
