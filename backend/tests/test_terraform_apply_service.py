"""Tests for TerraformApplyService remediation role separation."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from provisioning.terraform_apply_service import TerraformApplyService


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_request(cloud_account_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        cloud_account_id=cloud_account_id,
        request_number="REQ-TEST-001",
        status="APPROVED",
        evidence={},
    )


def _make_cloud_account(remediation_role_arn: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        auth_type="role_arn",
        role_arn="arn:aws:iam::123456789012:role/northbound-readonly",
        remediation_role_arn=remediation_role_arn,
        external_id=None,
        default_region="us-east-1",
    )


def _make_service(cloud_account: SimpleNamespace | None = None) -> TerraformApplyService:
    db = MagicMock()
    db.get.return_value = cloud_account
    service = TerraformApplyService(db=db)
    return service


# ── Remediation role guard ────────────────────────────────────────────────────

def test_apply_raises_if_remediation_role_arn_missing() -> None:
    account_id = uuid.uuid4()
    account = _make_cloud_account(remediation_role_arn=None)
    service = _make_service(cloud_account=account)
    request = _make_request(cloud_account_id=account_id)

    with pytest.raises(ValueError, match="remediation_role_arn"):
        service.apply(request)


def test_apply_error_message_mentions_remediation_role_arn() -> None:
    account_id = uuid.uuid4()
    account = _make_cloud_account(remediation_role_arn=None)
    service = _make_service(cloud_account=account)
    request = _make_request(cloud_account_id=account_id)

    with pytest.raises(ValueError) as exc_info:
        service.apply(request)
    assert "remediation_role_arn" in str(exc_info.value)


def test_apply_proceeds_to_precheck_when_remediation_role_arn_set() -> None:
    account_id = uuid.uuid4()
    account = _make_cloud_account(
        remediation_role_arn="arn:aws:iam::123456789012:role/northbound-remediation"
    )
    service = _make_service(cloud_account=account)
    service.precheck_service = MagicMock()
    service.precheck_service.run.return_value = MagicMock(
        passed=False,
        workspace_path=None,
        reasons=["Request status must be APPROVED"],
    )
    service.lock_service = MagicMock()
    request = _make_request(cloud_account_id=account_id)

    result = service.apply(request)

    # Did not raise; precheck was called
    service.precheck_service.run.assert_called_once()
    assert not result.apply_executed


def test_apply_no_cloud_account_id_skips_guard() -> None:
    service = _make_service(cloud_account=None)
    service.precheck_service = MagicMock()
    service.precheck_service.run.return_value = MagicMock(
        passed=False,
        workspace_path=None,
        reasons=["no account"],
    )
    service.lock_service = MagicMock()
    request = _make_request(cloud_account_id=None)

    # Should not raise; guard is skipped when there is no cloud_account_id
    result = service.apply(request)
    assert not result.apply_executed


def test_no_fallback_to_role_arn_when_remediation_role_arn_missing() -> None:
    account_id = uuid.uuid4()
    # Account has role_arn but no remediation_role_arn
    account = _make_cloud_account(remediation_role_arn=None)
    assert account.role_arn is not None  # role_arn exists — must NOT be used as fallback

    service = _make_service(cloud_account=account)
    request = _make_request(cloud_account_id=account_id)

    with pytest.raises(ValueError, match="remediation_role_arn"):
        service.apply(request)
    # Reaching here confirms apply did NOT fall back silently to role_arn


# ── Defensive: no silent fallback pattern in source ──────────────────────────

def test_no_silent_fallback_in_apply_service() -> None:
    import inspect
    import provisioning.terraform_apply_service as apply_module

    source = inspect.getsource(apply_module)
    assert "remediation_role_arn or role_arn" not in source
    assert "remediation_role_arn or cloud_account.role_arn" not in source
