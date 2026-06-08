from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningRequest
from provisioning.artifact_service import ProvisioningArtifactService
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.terraform_plan_parser import TerraformPlanParser
from provisioning.workspace_security import resolve_request_workspace


class RiskSummaryService:
    def __init__(
        self,
        db: Session,
        *,
        artifact_service: ProvisioningArtifactService | None = None,
        plan_parser: TerraformPlanParser | None = None,
    ) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.plan_parser = plan_parser or TerraformPlanParser()

    def generate(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> dict[str, Any]:
        workspace_path = resolve_request_workspace(request)
        plan_summary = self._plan_summary(workspace_path)
        security = (request.evidence or {}).get("security_scan") or {}
        cost = (request.evidence or {}).get("cost_estimate") or {}
        recommendation = self._recommendation(plan_summary=plan_summary, security=security)
        summary = {
            "request_id": request.request_number,
            "request_uuid": str(request.id),
            "template_key": request.template_key,
            "provider": request.provider,
            "environment": request.input_variables.get("environment") or request.tfvars_json.get("environment") or "unknown",
            "finding_id": str(request.finding_id) if request.finding_id else None,
            "terraform": plan_summary,
            "security": security,
            "cost": cost,
            "template_risk": request.risk_level,
            "approval_required": True,
            "recommendation": recommendation,
        }
        markdown = self._markdown(summary)
        self.artifact_service.create_json_file(
            request=request,
            artifact_type=ProvisioningArtifactType.RISK_SUMMARY_JSON,
            path=workspace_path / "risk-summary.json",
            workspace_root=workspace_path,
            payload=summary,
            created_by_user_id=created_by_user_id,
        )
        markdown_path = workspace_path / "risk-summary.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.RISK_SUMMARY_MARKDOWN,
            path=markdown_path,
            workspace_root=workspace_path,
            created_by_user_id=created_by_user_id,
            content_type="text/markdown",
            content_json={"request_id": request.request_number, "recommendation": recommendation},
        )
        request.status = ProvisioningRequestStatus.RISK_SUMMARY_READY.value
        request.evidence = {**(request.evidence or {}), "risk_summary": summary}
        self.db.commit()
        return summary

    def _plan_summary(self, workspace_path: Path) -> dict[str, Any]:
        plan_path = workspace_path / "plan.json"
        if not plan_path.exists():
            return {}
        return self.plan_parser.parse(json.loads(plan_path.read_text(encoding="utf-8")))

    def _recommendation(self, *, plan_summary: dict[str, Any], security: dict[str, Any]) -> str:
        if plan_summary.get("has_destructive_changes"):
            return "Do not proceed. Terraform plan includes destructive actions."
        if security.get("highest_severity") == "CRITICAL" or int(security.get("blocking_findings_count") or 0) > 0:
            return "Do not proceed. Security scan contains blocking findings."
        return "Ready to evaluate policy gates."

    def _money(self, value: Any) -> str:
        return "Unavailable" if value in (None, "") else f"${value}"

    def _markdown(self, summary: dict[str, Any]) -> str:
        terraform = summary["terraform"]
        security = summary["security"]
        cost = summary["cost"]
        return "\n".join(
            [
                f"# Risk Summary - {summary['request_id']}",
                "",
                "## Request",
                "",
                f"- Template: {summary['template_key']}",
                f"- Provider: {summary['provider']}",
                f"- Environment: {summary['environment']}",
                f"- Finding: {summary['finding_id'] or 'N/A'}",
                "",
                "## Terraform Plan",
                "",
                f"- Add: {terraform.get('add_count', 0)}",
                f"- Change: {terraform.get('change_count', 0)}",
                f"- Delete: {terraform.get('delete_count', 0)}",
                f"- Replace: {terraform.get('replace_count', 0)}",
                f"- Destructive Changes: {'Yes' if terraform.get('has_destructive_changes') else 'No'}",
                "",
                "## Security",
                "",
                f"- Passed Checks: {security.get('passed_count', 0)}",
                f"- Failed Checks: {security.get('failed_count', 0)}",
                f"- Blocking Findings: {security.get('blocking_findings_count', 0)}",
                f"- Highest Severity: {security.get('highest_severity', 'UNKNOWN')}",
                "",
                "## Cost",
                "",
                f"- Currency: {cost.get('currency', 'USD')}",
                f"- Projected Monthly Cost: {self._money(cost.get('total_monthly_cost'))}",
                f"- Monthly Diff: {self._money(cost.get('diff_total_monthly_cost'))}",
                "",
                "## Gate Decision",
                "",
                "Pending policy gate evaluation",
                "",
                "## Recommendation",
                "",
                summary["recommendation"],
                "",
            ]
        )
