from __future__ import annotations

from pathlib import Path

from models.provisioning_request import ProvisioningRequest
from provisioning.terraform_workspace import TerraformWorkspaceManager


def resolve_request_workspace(request: ProvisioningRequest, workspace_manager: TerraformWorkspaceManager | None = None) -> Path:
    if not request.workspace_path:
        raise ValueError("Terraform workspace is missing. Run nb terraform validate <request_id> first.")

    manager = workspace_manager or TerraformWorkspaceManager()
    workspace_path = Path(request.workspace_path).resolve()
    runtime_root = manager.runtime_root.resolve()
    if not workspace_path.is_relative_to(runtime_root):
        raise ValueError("Terraform workspace path is outside the allowed runtime directory.")
    if not workspace_path.is_dir():
        raise ValueError("Terraform workspace directory does not exist.")
    return workspace_path
