from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningArtifact, ProvisioningRequest
from provisioning.enums import ProvisioningArtifactType

SECRET_PATTERNS = [
    re.compile(r"(?i)(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|ANTHROPIC_API_KEY|OPENAI_API_KEY|DATABASE_URL|JWT_SECRET_KEY)\s*=\s*[^\s]+"),
    re.compile(r"(?i)(SECRET|TOKEN|PASSWORD|PRIVATE_KEY)([\"'\s:=]+)([^\"'\s,}]+)"),
]


def sanitize_sensitive_text(value: str) -> str:
    sanitized = value
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]" if len(match.groups()) == 1 else f"{match.group(1)}{match.group(2)}[REDACTED]", sanitized)
    return sanitized


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if any(token in key.upper() for token in ("SECRET", "TOKEN", "PASSWORD", "PRIVATE_KEY", "API_KEY")):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_json(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, str):
        return sanitize_sensitive_text(value)
    return value


class ProvisioningArtifactService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_file_artifact(
        self,
        *,
        request: ProvisioningRequest,
        artifact_type: ProvisioningArtifactType,
        path: Path,
        workspace_root: Path,
        created_by_user_id: str | None = None,
        content_type: str = "text/plain",
        content_json: dict[str, Any] | None = None,
    ) -> ProvisioningArtifact:
        resolved_path = path.resolve()
        resolved_root = workspace_root.resolve()
        if not resolved_path.is_relative_to(resolved_root):
            raise ValueError("Artifact path must stay inside the Terraform workspace.")
        if not resolved_path.exists():
            raise FileNotFoundError(f"Artifact file not found: {resolved_path.name}")
        data = resolved_path.read_bytes()
        artifact = ProvisioningArtifact(
            tenant_id=request.tenant_id,
            provisioning_request_id=request.id,
            artifact_type=artifact_type.value,
            name=resolved_path.name,
            content_json=sanitize_json(content_json or {}),
            content_type=content_type,
            storage_path=str(resolved_path),
            checksum=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            created_by_user_id=uuid.UUID(created_by_user_id) if created_by_user_id else None,
        )
        self.db.add(artifact)
        self.db.flush()
        return artifact

    def create_json_file(
        self,
        *,
        request: ProvisioningRequest,
        artifact_type: ProvisioningArtifactType,
        path: Path,
        workspace_root: Path,
        payload: dict[str, Any],
        created_by_user_id: str | None = None,
    ) -> ProvisioningArtifact:
        resolved_path = path.resolve()
        resolved_root = workspace_root.resolve()
        if not resolved_path.is_relative_to(resolved_root):
            raise ValueError("Artifact path must stay inside the Terraform workspace.")
        sanitized = sanitize_json(payload)
        path.write_text(json.dumps(sanitized, indent=2, sort_keys=True), encoding="utf-8")
        return self.create_file_artifact(
            request=request,
            artifact_type=artifact_type,
            path=path,
            workspace_root=workspace_root,
            created_by_user_id=created_by_user_id,
            content_type="application/json",
            content_json=sanitized,
        )

    def list_for_request(self, *, request: ProvisioningRequest) -> list[ProvisioningArtifact]:
        return list(
            self.db.scalars(
                select(ProvisioningArtifact)
                .where(ProvisioningArtifact.tenant_id == request.tenant_id)
                .where(ProvisioningArtifact.provisioning_request_id == request.id)
                .order_by(ProvisioningArtifact.created_at.asc())
            )
        )
