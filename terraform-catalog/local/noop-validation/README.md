# Local No-op Terraform Validation

This template exists for Phase C of Northbound Cloud Shell. It validates the Terraform runner, workspace, artifact and plan flow without calling AWS, OCI or any other cloud provider.

It must remain non-destructive. `terraform apply` and `terraform destroy` are not part of Phase C.
