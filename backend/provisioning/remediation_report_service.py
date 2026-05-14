from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.provisioning_request import PostRemediationValidation, ProvisioningArtifact, ProvisioningRequest
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_json
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus


class RemediationReportService:
    def __init__(self, db: Session, *, artifact_service: ProvisioningArtifactService | None = None) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)

    def generate(
        self,
        *,
        request: ProvisioningRequest,
        validation: PostRemediationValidation,
        workspace_path: Path,
        created_by_user_id: str | None = None,
    ) -> dict[str, Any]:
        request.status = ProvisioningRequestStatus.FINAL_REPORT_GENERATING.value
        evidence = self._evidence_list(request)
        payload = sanitize_json(
            {
                "request": {
                    "request_number": request.request_number,
                    "template_key": request.template_key,
                    "provider": request.provider,
                    "status": request.status,
                    "risk_level": request.risk_level,
                },
                "original_finding": validation.before_finding_snapshot_json,
                "plan_summary": (request.evidence or {}).get("terraform_plan", {}),
                "security_scan": (request.evidence or {}).get("security_scan", {}),
                "cost_estimate": (request.evidence or {}).get("cost_estimate", {}),
                "approval": (request.evidence or {}).get("approval", {}),
                "apply": (request.evidence or {}).get("terraform_apply", {}),
                "post_validation": {
                    "validation_code": validation.validation_code,
                    "result": validation.result,
                    "checks": validation.validation_checks_json,
                    "diff": validation.findings_diff_json,
                },
                "evidence": evidence,
                "final_decision": self._decision_text(validation.result),
                "recommendations": self._recommendation(validation.result),
            }
        )
        markdown = self._markdown(request, validation, payload)
        self.artifact_service.create_json_file(
            request=request,
            artifact_type=ProvisioningArtifactType.REMEDIATION_FINAL_REPORT_JSON,
            path=workspace_path / "remediation-final-report.json",
            workspace_root=workspace_path,
            payload=payload,
            created_by_user_id=created_by_user_id,
        )
        md_path = workspace_path / "remediation-final-report.md"
        md_path.write_text(markdown, encoding="utf-8")
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.REMEDIATION_FINAL_REPORT_MARKDOWN,
            path=md_path,
            workspace_root=workspace_path,
            created_by_user_id=created_by_user_id,
            content_type="text/markdown",
            content_json={"result": validation.result},
        )
        request.status = ProvisioningRequestStatus.FINAL_REPORT_READY.value
        return payload

    def latest_report_markdown(self, request: ProvisioningRequest) -> str | None:
        artifact = self.db.scalar(
            select(ProvisioningArtifact)
            .where(
                ProvisioningArtifact.provisioning_request_id == request.id,
                ProvisioningArtifact.artifact_type == ProvisioningArtifactType.REMEDIATION_FINAL_REPORT_MARKDOWN.value,
            )
            .order_by(ProvisioningArtifact.created_at.desc())
        )
        if artifact is None:
            return None
        if artifact.storage_path and Path(artifact.storage_path).exists():
            return Path(artifact.storage_path).read_text(encoding="utf-8")
        return None

    def _evidence_list(self, request: ProvisioningRequest) -> list[dict[str, str]]:
        artifacts = list(
            self.db.scalars(
                select(ProvisioningArtifact)
                .where(ProvisioningArtifact.provisioning_request_id == request.id)
                .order_by(ProvisioningArtifact.created_at.asc())
            )
        )
        return [{"type": artifact.artifact_type, "name": artifact.name, "checksum": artifact.checksum or ""} for artifact in artifacts]

    def _markdown(self, request: ProvisioningRequest, validation: PostRemediationValidation, payload: dict[str, Any]) -> str:
        finding = payload.get("original_finding", {})
        evidence = "\n".join(f"- {item['name']} ({item['type']})" for item in payload.get("evidence", []))
        checks = "\n".join(f"- {item['name']}: {item['status']}" for item in validation.validation_checks_json)
        return f"""# Remediation Final Report - {request.request_number}

## Executive Summary

Final decision: {validation.result}

## Request Metadata

- Template: {request.template_key}
- Provider: {request.provider}
- Request Status: {request.status}

## Original Finding

- Finding: {finding.get("id")}
- Rule: {finding.get("rule_id")}
- Severity: {finding.get("severity")}
- Title: {finding.get("title")}

## Validation Checks

{checks}

## Evidence List

{evidence}

## Final Decision

{self._decision_text(validation.result)}

## Recommendations

{self._recommendation(validation.result)}
"""

    def _decision_text(self, result: str) -> str:
        return {
            "RESOLVED": "The original finding was no longer active after post-remediation rescan.",
            "PARTIALLY_RESOLVED": "The remediation reduced risk but did not fully clear all related findings.",
            "STILL_OPEN": "The original finding remains active after remediation.",
            "VALIDATION_FAILED": "The platform could not verify remediation due to collector or data failure.",
        }.get(result, "Validation outcome is unknown.")

    def _recommendation(self, result: str) -> str:
        if result == "RESOLVED":
            return "Close remediation record and monitor next scheduled scan."
        if result == "PARTIALLY_RESOLVED":
            return "Review remaining related findings and plan a follow-up remediation."
        if result == "STILL_OPEN":
            return "Review apply output, template assumptions and latest inventory."
        return "Fix collector or findings data issues and rerun validation."
