from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningRequest
from provisioning.artifact_service import ProvisioningArtifactService
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.template_catalog import get_phase_c_execution_template
from provisioning.terraform_plan_parser import TerraformPlanParser
from provisioning.workspace_security import resolve_request_workspace


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
BLOCKED = "BLOCKED"


class PolicyGateEngine:
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

    def evaluate(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> dict[str, Any]:
        original_status = request.status
        request.status = ProvisioningRequestStatus.GATES_EVALUATING.value
        self.db.flush()

        gates = [
            self._request_not_cancelled(original_status),
            self._template_enabled(request),
            self._apply_disabled(),
        ]
        workspace_path: Path | None = None
        plan_summary: dict[str, Any] | None = None
        try:
            workspace_path = resolve_request_workspace(request)
            gates.append(self._plan_exists(workspace_path))
            plan_summary = self._plan_summary(workspace_path)
            gates.append(self._plan_status(original_status))
            gates.append(self._no_destructive_changes(plan_summary))
        except ValueError as exc:
            gates.append(self._gate("terraform_workspace", BLOCKED, str(exc)))

        gates.append(self._security_scan(request))
        gates.append(self._cost_estimate(request))

        blocked = any(gate["result"] == BLOCKED for gate in gates)
        failed = any(gate["result"] == FAIL for gate in gates)
        if blocked:
            final_status = ProvisioningRequestStatus.GATES_BLOCKED.value
            ready = False
        elif failed:
            final_status = ProvisioningRequestStatus.GATES_FAILED.value
            ready = False
        else:
            final_status = ProvisioningRequestStatus.READY_FOR_APPROVAL.value
            ready = True

        result = {
            "request_id": request.request_number,
            "status": final_status if not ready else ProvisioningRequestStatus.GATES_PASSED.value,
            "decision": final_status,
            "ready_for_approval": ready,
            "blocked": blocked,
            "gates": gates,
            "plan_summary": plan_summary or {},
        }
        request.status = final_status
        request.evidence = {**(request.evidence or {}), "policy_gates": result}
        if workspace_path:
            self.artifact_service.create_json_file(
                request=request,
                artifact_type=ProvisioningArtifactType.GATES_RESULT_JSON,
                path=workspace_path / "gates-result.json",
                workspace_root=workspace_path,
                payload=result,
                created_by_user_id=created_by_user_id,
            )
        self.db.commit()
        return result

    def _gate(self, name: str, result: str, message: str) -> dict[str, str]:
        return {"name": name, "result": result, "message": message}

    def _request_not_cancelled(self, status: str) -> dict[str, str]:
        if status == ProvisioningRequestStatus.CANCELLED.value:
            return self._gate("request_not_cancelled", BLOCKED, "Request is cancelled")
        return self._gate("request_not_cancelled", PASS, "Request is active")

    def _template_enabled(self, request: ProvisioningRequest) -> dict[str, str]:
        template = get_phase_c_execution_template(request.template_key)
        if not template.terraform_enabled:
            return self._gate("template_enabled", BLOCKED, "Terraform execution template is disabled")
        return self._gate("template_enabled", PASS, "Terraform execution template is enabled")

    def _apply_disabled(self) -> dict[str, str]:
        return self._gate("apply_disabled", PASS, "Terraform apply remains disabled in Phase D")

    def _plan_exists(self, workspace_path: Path) -> dict[str, str]:
        if (workspace_path / "plan.json").is_file():
            return self._gate("terraform_plan_exists", PASS, "plan.json found")
        return self._gate("terraform_plan_exists", BLOCKED, "plan.json not found")

    def _plan_status(self, status: str) -> dict[str, str]:
        allowed = {
            ProvisioningRequestStatus.PLAN_READY.value,
            ProvisioningRequestStatus.SECURITY_SCAN_PASSED.value,
            ProvisioningRequestStatus.SECURITY_SCAN_BLOCKED.value,
            ProvisioningRequestStatus.COST_ESTIMATE_READY.value,
            ProvisioningRequestStatus.COST_ESTIMATE_FAILED.value,
            ProvisioningRequestStatus.RISK_SUMMARY_READY.value,
            ProvisioningRequestStatus.GATES_EVALUATING.value,
            ProvisioningRequestStatus.GATES_FAILED.value,
            ProvisioningRequestStatus.GATES_BLOCKED.value,
            ProvisioningRequestStatus.READY_FOR_APPROVAL.value,
        }
        if status in allowed:
            return self._gate("terraform_plan_status", PASS, "Plan workflow has reached a post-plan status")
        return self._gate("terraform_plan_status", BLOCKED, f"Request status is {status}, not PLAN_READY")

    def _plan_summary(self, workspace_path: Path) -> dict[str, Any]:
        plan_path = workspace_path / "plan.json"
        if not plan_path.exists():
            return {}
        return self.plan_parser.parse(json.loads(plan_path.read_text(encoding="utf-8")))

    def _no_destructive_changes(self, summary: dict[str, Any] | None) -> dict[str, str]:
        if not summary:
            return self._gate("no_destructive_changes", BLOCKED, "Terraform plan summary is unavailable")
        if summary.get("has_destructive_changes"):
            return self._gate("no_destructive_changes", BLOCKED, "Terraform plan includes delete or replace actions")
        return self._gate("no_destructive_changes", PASS, "No delete or replace actions detected")

    def _security_scan(self, request: ProvisioningRequest) -> dict[str, str]:
        summary = (request.evidence or {}).get("security_scan") or {}
        if not summary:
            return self._gate("security_scan", BLOCKED, "Security scan evidence not found")
        if summary.get("tool_available") is False:
            return self._gate("security_scan", FAIL, str(summary.get("reason") or "Checkov unavailable"))
        if summary.get("highest_severity") == "CRITICAL":
            return self._gate("security_scan", BLOCKED, "Critical Checkov finding detected")
        if int(summary.get("blocking_findings_count") or 0) > 0:
            return self._gate("security_scan", BLOCKED, "Blocked high-risk Checkov finding detected")
        return self._gate("security_scan", PASS, "No critical findings detected")

    def _cost_estimate(self, request: ProvisioningRequest) -> dict[str, str]:
        summary = (request.evidence or {}).get("cost_estimate") or {}
        if not summary:
            return self._gate("cost_estimate", WARN, "Cost estimate not found")
        if summary.get("available") is False:
            return self._gate("cost_estimate", WARN, str(summary.get("reason") or "Cost estimate unavailable"))
        return self._gate("cost_estimate", PASS, "Cost estimate available")
