from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from models.provisioning_request import ProvisioningRequest
from provisioning.template_catalog import TerraformTemplateDefinition


@dataclass(frozen=True)
class WorkspaceResult:
    workspace_path: Path
    template_path: Path
    tfvars_path: Path
    metadata_path: Path


class TerraformWorkspaceManager:
    def __init__(self, *, repo_root: Path | None = None, runtime_root: Path | None = None) -> None:
        self.repo_root = (repo_root or self._detect_repo_root()).resolve()
        self.runtime_root = (runtime_root or self.repo_root / "runtime" / "terraform-workspaces").resolve()

    def _detect_repo_root(self) -> Path:
        current = Path(__file__).resolve()
        backend_root = current.parents[1]
        project_root = current.parents[2]
        if (project_root / "backend").is_dir():
            return project_root
        return backend_root

    def prepare_workspace(
        self,
        *,
        request: ProvisioningRequest,
        template: TerraformTemplateDefinition,
        tfvars: dict[str, Any],
    ) -> WorkspaceResult:
        request_code = self.safe_request_code(request.request_number)
        workspace_path = (self.runtime_root / request_code).resolve()
        if not workspace_path.is_relative_to(self.runtime_root):
            raise ValueError("Invalid Terraform workspace path.")

        template_path = (self.repo_root / template.module_path).resolve()
        if not template_path.is_dir():
            raise FileNotFoundError(f"Terraform template path not found: {template.module_path}")
        if not template_path.is_relative_to(self.repo_root):
            raise ValueError("Terraform template path must stay inside the repository.")

        workspace_path.mkdir(parents=True, exist_ok=True)
        self._copy_template_files(template_path=template_path, workspace_path=workspace_path)
        tfvars_path = workspace_path / "terraform.tfvars.json"
        tfvars_path.write_text(json.dumps(tfvars, indent=2, sort_keys=True), encoding="utf-8")
        metadata_path = workspace_path / "execution-metadata.json"
        metadata = {
            "request_code": request.request_number,
            "request_id": str(request.id),
            "remediation_template_key": request.template_key,
            "execution_template_key": template.key,
            "terraform_apply_enabled": False,
            "terraform_destroy_enabled": False,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        return WorkspaceResult(workspace_path=workspace_path, template_path=template_path, tfvars_path=tfvars_path, metadata_path=metadata_path)

    def safe_request_code(self, request_code: str) -> str:
        if not re.fullmatch(r"REQ-[A-Za-z0-9_-]+", request_code):
            raise ValueError("Invalid request code for Terraform workspace.")
        return request_code

    def _copy_template_files(self, *, template_path: Path, workspace_path: Path) -> None:
        allowed_suffixes = {".tf", ".tf.json"}
        for source in template_path.iterdir():
            if not source.is_file() or source.name == "terraform.tfvars.json":
                continue
            if source.suffix not in allowed_suffixes:
                continue
            shutil.copy2(source, workspace_path / source.name)
