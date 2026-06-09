from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from collectors.aws.session import AWSSessionFactory, build_role_session_name


# ── build_role_session_name ───────────────────────────────────────────────────

def test_session_name_no_user_defaults_to_svc() -> None:
    assert build_role_session_name() == "nb-svc-scan"


def test_session_name_no_user_explicit_none() -> None:
    assert build_role_session_name(user_id=None, operation="scan") == "nb-svc-scan"


def test_session_name_with_user_id() -> None:
    result = build_role_session_name(user_id="a1b2c3d4-9999-8888", operation="scan")
    assert result.startswith("nb-a1b2c3d4-scan")


def test_session_name_user_id_truncated_to_8_chars() -> None:
    result = build_role_session_name(user_id="abcdef1234567890", operation="scan")
    assert result == "nb-abcdef12-scan"


def test_session_name_apply_with_request_number() -> None:
    result = build_role_session_name(user_id="a1b2c3d4-9999", operation="apply", request_number="REQ-0042")
    assert result == "nb-a1b2c3d4-apply-REQ-0042"


def test_session_name_operation_underscore_replaced() -> None:
    result = build_role_session_name(user_id=None, operation="inventory_scan")
    assert result == "nb-svc-inventory-scan"


def test_session_name_invalid_chars_stripped() -> None:
    result = build_role_session_name(user_id="ab!cd#12", operation="scan")
    # ! and # are stripped, leaving "abcd12"
    assert "!" not in result
    assert "#" not in result


def test_session_name_max_64_chars() -> None:
    long_req = "REQ-" + "9" * 60
    result = build_role_session_name(user_id="a1b2c3d4", operation="apply", request_number=long_req)
    assert len(result) <= 64


# ── AWSSessionFactory.create_session — role_arn path ─────────────────────────

def _make_role_arn_account(external_id: str | None = "ext-secret-42") -> SimpleNamespace:
    return SimpleNamespace(
        auth_type="role_arn",
        role_arn="arn:aws:iam::123456789012:role/northbound-readonly",
        external_id=external_id,
        default_region="us-east-1",
    )


def _fake_sts_response() -> dict:
    return {
        "Credentials": {
            "AccessKeyId": "ASIA_FAKE",
            "SecretAccessKey": "fake-secret",
            "SessionToken": "fake-token",
        }
    }


def test_assume_role_uses_traceable_session_name(monkeypatch) -> None:
    account = _make_role_arn_account()
    captured: dict = {}

    mock_sts = MagicMock()
    mock_sts.assume_role.side_effect = lambda **kw: (captured.update(kw), _fake_sts_response())[1]

    mock_base_session = MagicMock()
    mock_base_session.client.return_value = mock_sts

    with patch("collectors.aws.session.boto3.Session", return_value=mock_base_session):
        factory = AWSSessionFactory(account, timeout_seconds=30, user_id="a1b2c3d4", operation="scan")
        factory.create_session()

    assert captured["RoleSessionName"] == "nb-a1b2c3d4-scan"


def test_assume_role_preserves_external_id(monkeypatch) -> None:
    account = _make_role_arn_account(external_id="ext-secret-42")
    captured: dict = {}

    mock_sts = MagicMock()
    mock_sts.assume_role.side_effect = lambda **kw: (captured.update(kw), _fake_sts_response())[1]

    mock_base_session = MagicMock()
    mock_base_session.client.return_value = mock_sts

    with patch("collectors.aws.session.boto3.Session", return_value=mock_base_session):
        AWSSessionFactory(account, timeout_seconds=30).create_session()

    assert captured["ExternalId"] == "ext-secret-42"


def test_assume_role_no_external_id_when_absent(monkeypatch) -> None:
    account = _make_role_arn_account(external_id=None)
    captured: dict = {}

    mock_sts = MagicMock()
    mock_sts.assume_role.side_effect = lambda **kw: (captured.update(kw), _fake_sts_response())[1]

    mock_base_session = MagicMock()
    mock_base_session.client.return_value = mock_sts

    with patch("collectors.aws.session.boto3.Session", return_value=mock_base_session):
        AWSSessionFactory(account, timeout_seconds=30).create_session()

    assert "ExternalId" not in captured


def test_assume_role_no_user_uses_svc(monkeypatch) -> None:
    account = _make_role_arn_account()
    captured: dict = {}

    mock_sts = MagicMock()
    mock_sts.assume_role.side_effect = lambda **kw: (captured.update(kw), _fake_sts_response())[1]

    mock_base_session = MagicMock()
    mock_base_session.client.return_value = mock_sts

    with patch("collectors.aws.session.boto3.Session", return_value=mock_base_session):
        AWSSessionFactory(account, timeout_seconds=30).create_session()

    assert captured["RoleSessionName"] == "nb-svc-scan"


# ── Defensive: hardcoded string is gone ──────────────────────────────────────

def test_hardcoded_session_name_removed() -> None:
    import inspect
    import collectors.aws.session as session_module

    source = inspect.getsource(session_module)
    assert "northbound-control-tower-inventory" not in source
