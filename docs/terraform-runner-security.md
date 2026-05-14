# Terraform Runner Security

Northbound Terraform execution is a controlled service, not a shell.

## Command Allowlist

Only these commands are allowed in Phase C:

```text
terraform init -input=false -no-color
terraform validate -no-color
terraform plan -out=plan.out -input=false -no-color
terraform show -json plan.out
```

The runner executes commands as argument lists with `subprocess.run`. It does not use `shell=True`.

## Blocked Commands

The Cloud Shell parser and registry block or disable:

```text
terraform apply
terraform apply -auto-approve
terraform destroy
terraform force-unlock
terraform import
terraform state rm
terraform state mv
bash
sh
zsh
aws s3 rm
aws iam delete-role
```

## Workspace Isolation

Each request gets a workspace under:

```text
runtime/terraform-workspaces/<request_code>/
```

The workspace manager validates request codes and rejects path traversal.

## Secret Handling

Logs and JSON metadata pass through basic redaction for fields and values that look like secrets, tokens, private keys, passwords, API keys or connection strings.

## Timeouts

Terraform commands have a fixed timeout to avoid stuck worker processes.

## No Infrastructure Mutation

Phase C generates plans only. Apply and destroy remain unavailable. Later phases must add security gates, cost review and human approval before any mutation is considered.
