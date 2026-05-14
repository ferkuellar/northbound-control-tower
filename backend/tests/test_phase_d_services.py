from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace

from provisioning.cost_estimation_service import CostEstimationService
from provisioning.enums import ProvisioningRequestStatus
from provisioning.policy_gates import BLOCKED, WARN, PolicyGateEngine
from provisioning.risk_summary_service import RiskSummaryService
from provisioning.security_scan_service import SecurityScanService


class FakeDb:
    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass


class FakeArtifactService:
    def __init__(self) -> None:
        self.artifacts: list[tuple[str, str]] = []

    def create_json_file(self, *, artifact_type, path: Path, payload, **kwargs):
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.artifacts.append((artifact_type.value, path.name))
        return SimpleNamespace(storage_path=str(path), name=path.name)

    def create_file_artifact(self, *, artifact_type, path: Path, **kwargs):
        self.artifacts.append((artifact_type.value, path.name))
        return SimpleNamespace(storage_path=str(path), name=path.name)


def _request(workspace: Path) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        request_number="REQ-1001",
        tenant_id=uuid.uuid4(),
        cloud_account_id=None,
        finding_id=uuid.uuid4(),
        requested_by_user_id=None,
        provider="AWS",
        template_key="local-noop-validation",
        template_version="v0",
        status=ProvisioningRequestStatus.PLAN_READY.value,
        risk_level="LOW",
        title="Demo",
        description="Demo",
        input_variables={},
        tfvars_json={},
        workspace_path=str(workspace),
        evidence={},
        approval_required=False,
    )


def _write_plan(workspace: Path, actions: list[str]) -> None:
    (workspace / "plan.json").write_text(
        json.dumps({"resource_changes": [{"provider_name": "registry.terraform.io/hashicorp/local", "change": {"actions": actions}}]}),
        encoding="utf-8",
    )


def test_security_scan_service_runs_checkov_without_shell_and_saves_artifacts(monkeypatch, tmp_path: Path) -> None:
    request = _request(tmp_path)
    artifacts = FakeArtifactService()

    def fake_runner(command, **kwargs):
        assert command == ["checkov", "-d", str(tmp_path), "-o", "json"]
        assert "shell" not in kwargs
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"results": {"passed_checks": [{}]}}), stderr="")

    monkeypatch.setattr("provisioning.security_scan_service.resolve_request_workspace", lambda request: tmp_path)

    result = SecurityScanService(FakeDb(), artifact_service=artifacts, runner=fake_runner).scan(request)

    assert result.status == ProvisioningRequestStatus.SECURITY_SCAN_PASSED.value
    assert ("CHECKOV_JSON", "checkov.json") in artifacts.artifacts
    assert ("CHECKOV_LOG", "checkov.log") in artifacts.artifacts


def test_security_scan_service_handles_missing_checkov(monkeypatch, tmp_path: Path) -> None:
    request = _request(tmp_path)

    def fake_runner(command, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("provisioning.security_scan_service.resolve_request_workspace", lambda request: tmp_path)

    result = SecurityScanService(FakeDb(), artifact_service=FakeArtifactService(), runner=fake_runner).scan(request)

    assert result.status == ProvisioningRequestStatus.SECURITY_SCAN_FAILED.value
    assert result.summary["tool_available"] is False


def test_cost_service_runs_infracost_without_shell_and_saves_artifacts(monkeypatch, tmp_path: Path) -> None:
    request = _request(tmp_path)
    artifacts = FakeArtifactService()

    def fake_runner(command, **kwargs):
        assert command[:2] == ["infracost", "breakdown"]
        assert "shell" not in kwargs
        (tmp_path / "infracost.json").write_text(json.dumps({"currency": "USD", "totalMonthlyCost": "0"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setenv("INFRACOST_API_KEY", "test-key")
    monkeypatch.setattr("provisioning.cost_estimation_service.resolve_request_workspace", lambda request: tmp_path)

    result = CostEstimationService(FakeDb(), artifact_service=artifacts, runner=fake_runner).estimate(request)

    assert result.status == ProvisioningRequestStatus.COST_ESTIMATE_READY.value
    assert ("INFRACOST_JSON", "infracost.json") in artifacts.artifacts
    assert ("INFRACOST_LOG", "infracost.log") in artifacts.artifacts


def test_cost_service_handles_missing_api_key(monkeypatch, tmp_path: Path) -> None:
    request = _request(tmp_path)
    monkeypatch.delenv("INFRACOST_API_KEY", raising=False)
    monkeypatch.setattr("provisioning.cost_estimation_service.resolve_request_workspace", lambda request: tmp_path)

    result = CostEstimationService(FakeDb(), artifact_service=FakeArtifactService()).estimate(request)

    assert result.status == ProvisioningRequestStatus.COST_ESTIMATE_FAILED.value
    assert result.summary["available"] is False


def test_policy_gates_pass_with_cost_warning(monkeypatch, tmp_path: Path) -> None:
    _write_plan(tmp_path, ["create"])
    request = _request(tmp_path)
    request.evidence = {
        "security_scan": {"tool_available": True, "highest_severity": "UNKNOWN", "blocking_findings_count": 0},
        "cost_estimate": {"available": False, "reason": "Infracost unavailable in local environment"},
    }
    monkeypatch.setattr("provisioning.policy_gates.resolve_request_workspace", lambda request: tmp_path)

    result = PolicyGateEngine(FakeDb(), artifact_service=FakeArtifactService()).evaluate(request)

    assert result["ready_for_approval"] is True
    assert request.status == ProvisioningRequestStatus.READY_FOR_APPROVAL.value
    assert any(gate["result"] == WARN for gate in result["gates"])


def test_policy_gates_block_destructive_and_critical(monkeypatch, tmp_path: Path) -> None:
    _write_plan(tmp_path, ["delete"])
    request = _request(tmp_path)
    request.evidence = {
        "security_scan": {"tool_available": True, "highest_severity": "CRITICAL", "blocking_findings_count": 1},
        "cost_estimate": {"available": True},
    }
    monkeypatch.setattr("provisioning.policy_gates.resolve_request_workspace", lambda request: tmp_path)

    result = PolicyGateEngine(FakeDb(), artifact_service=FakeArtifactService()).evaluate(request)

    assert result["blocked"] is True
    assert request.status == ProvisioningRequestStatus.GATES_BLOCKED.value
    assert any(gate["result"] == BLOCKED for gate in result["gates"])


def test_policy_gates_block_cancelled_request(monkeypatch, tmp_path: Path) -> None:
    _write_plan(tmp_path, ["create"])
    request = _request(tmp_path)
    request.status = ProvisioningRequestStatus.CANCELLED.value
    request.evidence = {"security_scan": {"tool_available": True, "blocking_findings_count": 0}, "cost_estimate": {"available": True}}
    monkeypatch.setattr("provisioning.policy_gates.resolve_request_workspace", lambda request: tmp_path)

    result = PolicyGateEngine(FakeDb(), artifact_service=FakeArtifactService()).evaluate(request)

    assert result["blocked"] is True
    assert any(gate["name"] == "request_not_cancelled" and gate["result"] == BLOCKED for gate in result["gates"])


def test_risk_summary_generates_json_and_markdown(monkeypatch, tmp_path: Path) -> None:
    _write_plan(tmp_path, ["create"])
    request = _request(tmp_path)
    request.evidence = {
        "security_scan": {"passed_count": 1, "failed_count": 0, "blocking_findings_count": 0},
        "cost_estimate": {"currency": "USD", "total_monthly_cost": "0.00", "diff_total_monthly_cost": "0.00"},
    }
    artifacts = FakeArtifactService()
    monkeypatch.setattr("provisioning.risk_summary_service.resolve_request_workspace", lambda request: tmp_path)

    summary = RiskSummaryService(FakeDb(), artifact_service=artifacts).generate(request)

    assert summary["terraform"]["add_count"] == 1
    assert (tmp_path / "risk-summary.json").exists()
    assert (tmp_path / "risk-summary.md").exists()
    assert request.status == ProvisioningRequestStatus.RISK_SUMMARY_READY.value
