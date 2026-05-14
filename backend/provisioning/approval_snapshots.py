from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningArtifact, ProvisioningRequest
from provisioning.enums import ProvisioningArtifactType


def artifact_by_type(db: Session, request: ProvisioningRequest, artifact_type: ProvisioningArtifactType) -> ProvisioningArtifact | None:
    return db.scalar(
        select(ProvisioningArtifact)
        .where(ProvisioningArtifact.provisioning_request_id == request.id)
        .where(ProvisioningArtifact.artifact_type == artifact_type.value)
        .order_by(ProvisioningArtifact.created_at.desc())
    )


def approval_snapshots(db: Session, request: ProvisioningRequest) -> dict[str, Any]:
    risk_artifact = artifact_by_type(db, request, ProvisioningArtifactType.RISK_SUMMARY_JSON)
    gates_artifact = artifact_by_type(db, request, ProvisioningArtifactType.GATES_RESULT_JSON)
    plan_artifact = artifact_by_type(db, request, ProvisioningArtifactType.TERRAFORM_PLAN_JSON)
    plan_binary_artifact = artifact_by_type(db, request, ProvisioningArtifactType.TERRAFORM_PLAN_BINARY)

    evidence = request.evidence or {}
    risk_summary = risk_artifact.content_json if risk_artifact else evidence.get("risk_summary") or {}
    gates = gates_artifact.content_json if gates_artifact else evidence.get("policy_gates") or {}
    security = evidence.get("security_scan") or risk_summary.get("security") or {}
    cost = evidence.get("cost_estimate") or risk_summary.get("cost") or {}
    plan_summary = evidence.get("terraform_plan") or risk_summary.get("terraform") or gates.get("plan_summary") or {}

    return {
        "risk_summary": risk_summary,
        "gates": gates,
        "security": security,
        "cost": cost,
        "plan_summary": plan_summary,
        "checksums": {
            "plan": plan_binary_artifact.checksum if plan_binary_artifact else None,
            "plan_json": plan_artifact.checksum if plan_artifact else None,
            "risk_summary": risk_artifact.checksum if risk_artifact else None,
            "gates_result": gates_artifact.checksum if gates_artifact else None,
        },
    }
