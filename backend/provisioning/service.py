from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.finding import Finding
from models.provisioning_request import ProvisioningArtifact, ProvisioningRequest
from models.user import User
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.template_catalog import TerraformTemplateDefinition, template_for_finding_type


def _next_request_number(db: Session) -> tuple[str, int]:
    count = db.scalar(select(func.count()).select_from(ProvisioningRequest)) or 0
    sequence = int(count) + 1001
    return f"REQ-{sequence}", sequence


def build_tfvars(finding: Finding, template: TerraformTemplateDefinition, request_number: str | None = None) -> dict[str, Any]:
    return {
        "request_code": request_number,
        "provider": finding.provider,
        "finding_id": str(finding.id),
        "cloud_account_id": str(finding.cloud_account_id),
        "resource_id": str(finding.resource_id) if finding.resource_id else None,
        "finding_type": finding.finding_type,
        "template_key": template.key,
        "phase": "B",
        "terraform_execution_enabled": False,
    }


class ProvisioningRequestService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_from_finding(self, *, finding: Finding, current_user: User | None) -> ProvisioningRequest:
        template = template_for_finding_type(finding.finding_type, finding.provider)
        request_number, sequence = _next_request_number(self.db)
        tfvars = build_tfvars(finding, template, request_number)
        evidence = {
            "source": "cloud_shell",
            "phase": "B",
            "finding_title": finding.title,
            "finding_type": finding.finding_type,
            "template_module_path": template.module_path,
            "phase_c_execution_template": "local-noop-validation",
            "terraform_execution": "disabled",
            "approval": "not_available_in_phase_b",
            "notes": [
                "Request is a draft.",
                "Terraform validate/plan/apply are disabled until later phases.",
                "No cloud API calls were executed.",
            ],
        }
        request = ProvisioningRequest(
            request_number=request_number,
            created_at_sequence=sequence,
            tenant_id=finding.tenant_id,
            cloud_account_id=finding.cloud_account_id,
            finding_id=finding.id,
            requested_by_user_id=current_user.id if current_user else None,
            provider=finding.provider,
            template_key=template.key,
            template_version="v0",
            status=ProvisioningRequestStatus.DRAFT.value,
            risk_level=template.risk_level,
            title=f"Draft remediation for {finding.title}",
            description=template.description,
            input_variables={
                "finding_id": str(finding.id),
                "finding_type": finding.finding_type,
                "provider": finding.provider,
                "resource_id": str(finding.resource_id) if finding.resource_id else None,
            },
            tfvars_json=tfvars,
            workspace_path=None,
            evidence=evidence,
            approval_required=template.risk_level in {"HIGH", "CRITICAL"},
        )
        self.db.add(request)
        self.db.flush()
        self._create_artifact(request, ProvisioningArtifactType.REQUEST_INPUT, "request-input.json", request.input_variables)
        self._create_artifact(request, ProvisioningArtifactType.TFVARS, "terraform.tfvars.json", tfvars)
        self._create_artifact(request, ProvisioningArtifactType.EVIDENCE, "phase-b-evidence.json", evidence)
        self.db.commit()
        self.db.refresh(request)
        return request

    def list_requests(self, *, tenant_id: uuid.UUID, limit: int = 20) -> list[ProvisioningRequest]:
        return list(
            self.db.scalars(
                select(ProvisioningRequest)
                .where(ProvisioningRequest.tenant_id == tenant_id)
                .order_by(ProvisioningRequest.created_at.desc())
                .limit(limit)
            )
        )

    def get_by_number_or_id(self, *, tenant_id: uuid.UUID, identifier: str) -> ProvisioningRequest | None:
        query = select(ProvisioningRequest).where(ProvisioningRequest.tenant_id == tenant_id)
        try:
            return self.db.scalar(query.where(ProvisioningRequest.id == uuid.UUID(identifier)))
        except ValueError:
            return self.db.scalar(query.where(ProvisioningRequest.request_number == identifier))

    def list_artifacts(self, *, request: ProvisioningRequest) -> list[ProvisioningArtifact]:
        return list(
            self.db.scalars(
                select(ProvisioningArtifact)
                .where(ProvisioningArtifact.tenant_id == request.tenant_id, ProvisioningArtifact.provisioning_request_id == request.id)
                .order_by(ProvisioningArtifact.created_at.asc())
            )
        )

    def _create_artifact(
        self,
        request: ProvisioningRequest,
        artifact_type: ProvisioningArtifactType,
        name: str,
        content: dict[str, Any],
    ) -> ProvisioningArtifact:
        checksum = hashlib.sha256(str(sorted(content.items())).encode("utf-8")).hexdigest()
        artifact = ProvisioningArtifact(
            tenant_id=request.tenant_id,
            provisioning_request_id=request.id,
            artifact_type=artifact_type.value,
            name=name,
            content_json=content,
            checksum=checksum,
        )
        self.db.add(artifact)
        return artifact
