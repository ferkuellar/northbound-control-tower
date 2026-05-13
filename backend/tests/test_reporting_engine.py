import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from ai.enums import AIAnalysisStatus, AIAnalysisType, AIProvider
from api.main import app
from auth.dependencies import get_current_user
from core.database import SessionLocal, get_db
from models.ai_analysis import AIAnalysis
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from models.user import User, UserRole
from reports.branding import merge_branding
from reports.context_builder import ReportContextBuilder
from reports.enums import ReportType
from reports.html_renderer import HTMLReportRenderer
from reports.pdf_renderer import PDFReportRenderer
from reports.validators import validate_report_html


def _db_override() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_report_user(role: UserRole = UserRole.ADMIN, *, with_ai: bool = True) -> User:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Report Tenant {suffix}", slug=f"report-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"report-{role.value.lower()}-{suffix}@northbound.local",
        full_name="Report User",
        hashed_password="not-used",
        role=role.value,
        is_active=True,
    )
    account = CloudAccount(
        tenant_id=tenant.id,
        provider="aws",
        name="AWS Report",
        auth_type="profile",
        access_key_id="AKIA_SHOULD_NOT_RENDER",
        secret_access_key="secret-should-not-render",
        default_region="us-east-1",
        is_active=True,
    )
    db.add_all([user, account])
    db.flush()
    resource = Resource(
        tenant_id=tenant.id,
        cloud_account_id=account.id,
        provider="aws",
        resource_type="compute",
        resource_id="i-report-test",
        fingerprint=uuid.uuid4().hex,
        name="report-test-instance",
        region="us-east-1",
        lifecycle_status="running",
        exposure_level="public",
        environment="prod",
        tags={"owner": "platform"},
        metadata_json={"private_key": "-----BEGIN PRIVATE KEY-----bad", "cpu_count": 2},
        relationships={},
    )
    finding = Finding(
        tenant_id=tenant.id,
        cloud_account_id=account.id,
        resource=resource,
        provider="aws",
        finding_type="public_exposure",
        category="security",
        severity="high",
        status="open",
        title="Public exposure detected",
        description="Resource is public",
        evidence={"secret_access_key": "do-not-render", "public_ip": "203.0.113.10"},
        recommendation="Validate exposure before making changes.",
        rule_id="public_exposure_v1",
        fingerprint=uuid.uuid4().hex,
    )
    score = CloudScore(
        tenant_id=tenant.id,
        cloud_account_id=None,
        provider=None,
        score_type="overall",
        score_value=72,
        grade="fair",
        trend="stable",
        summary="overall score is 72",
        evidence={"total_findings": 1},
    )
    db.add_all([resource, finding, score])
    if with_ai:
        db.add(
            AIAnalysis(
                tenant_id=tenant.id,
                cloud_account_id=None,
                provider=None,
                ai_provider=AIProvider.DEEPSEEK.value,
                analysis_type=AIAnalysisType.FULL_ASSESSMENT.value,
                status=AIAnalysisStatus.COMPLETED.value,
                input_summary={"sanitized": True},
                output={
                    "executive_summary": "Leadership risk summary.",
                    "technical_assessment": "Technical assessment.",
                    "remediation_recommendations": ["Validate approval, backup, snapshot, and rollback."],
                },
                raw_text=None,
                model_name="fake-model",
                prompt_version="test",
                created_by_user_id=user.id,
            )
        )
    db.commit()
    db.refresh(user)
    db.expunge(user)
    db.close()
    return user


def _client_for(user: User) -> TestClient:
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_report_context_sanitizes_secrets_and_includes_summaries() -> None:
    user = _seed_report_user()
    db = SessionLocal()
    try:
        context = ReportContextBuilder(db).build(tenant_id=user.tenant_id, report_type=ReportType.EXECUTIVE)
        serialized = str(context)

        assert context["scores"]["overall"] == 72
        assert context["findings_summary"]["total"] == 1
        assert context["inventory_summary"]["total_resources"] == 1
        assert "secret-should-not-render" not in serialized
        assert "PRIVATE KEY" not in serialized
        assert "do-not-render" not in serialized
    finally:
        db.close()


def test_report_context_handles_missing_ai_analysis() -> None:
    user = _seed_report_user(with_ai=False)
    db = SessionLocal()
    try:
        context = ReportContextBuilder(db).build(tenant_id=user.tenant_id, report_type=ReportType.TECHNICAL)

        assert context["ai"]["available"] is False
        assert context["limitations"]
    finally:
        db.close()


def test_templates_render_required_sections() -> None:
    user = _seed_report_user()
    db = SessionLocal()
    try:
        context = ReportContextBuilder(db).build(tenant_id=user.tenant_id, report_type=ReportType.EXECUTIVE)
        html = HTMLReportRenderer().render(
            report_type=ReportType.EXECUTIVE,
            context=context,
            branding=merge_branding({"company_name": "Northbound Demo"}),
            title="Executive Test Report",
        )

        assert "Cover Page" in html
        assert "Executive Summary" in html
        assert "Cloud Operational Score" in html
        validate_report_html(title="Executive Test Report", html=html, report_type=ReportType.EXECUTIVE)
    finally:
        db.close()


def test_report_validator_blocks_secret_patterns() -> None:
    with pytest.raises(Exception):
        validate_report_html(
            title="Bad Report",
            html="<html><body>Cover Page Executive Summary -----BEGIN PRIVATE KEY-----</body></html>",
            report_type=ReportType.EXECUTIVE,
        )


def test_pdf_generation_creates_safe_file(tmp_path) -> None:
    renderer = PDFReportRenderer(storage_root=tmp_path)
    tenant_id = uuid.uuid4()
    report_id = uuid.uuid4()

    result = renderer.render_to_file(html="<html><title>PDF Test</title><body>Report</body></html>", tenant_id=tenant_id, report_id=report_id)

    path = tmp_path / str(tenant_id) / f"{report_id}.pdf"
    assert path.exists()
    assert path.read_bytes().startswith(b"%PDF")
    assert result["checksum"]


def test_report_generation_requires_auth() -> None:
    _clear_overrides()
    client = TestClient(app)

    response = client.post("/api/v1/reports/generate", json={"report_type": "executive", "report_format": "html"})

    assert response.status_code == 401


def test_viewer_cannot_generate_report() -> None:
    user = _seed_report_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/reports/generate", json={"report_type": "executive", "report_format": "html"})

        assert response.status_code == 403
    finally:
        _clear_overrides()


def test_analyst_can_generate_preview_and_download_report() -> None:
    user = _seed_report_user(UserRole.ANALYST)
    client = _client_for(user)
    try:
        create_response = client.post(
            "/api/v1/reports/generate",
            json={
                "report_type": "executive",
                "report_format": "html",
                "branding": {"company_name": "Northbound Demo", "primary_color": "#0f172a", "secondary_color": "#1e293b"},
            },
        )
        assert create_response.status_code == 201
        report_id = create_response.json()["report"]["id"]

        preview_response = client.get(f"/api/v1/reports/{report_id}/preview")
        download_response = client.get(f"/api/v1/reports/{report_id}/download")

        assert preview_response.status_code == 200
        assert "Northbound Demo" in preview_response.text
        assert "secret-should-not-render" not in preview_response.text
        assert download_response.status_code == 200
        assert "Northbound Demo" in download_response.text
    finally:
        _clear_overrides()


def test_report_list_is_tenant_isolated() -> None:
    user = _seed_report_user(UserRole.ADMIN)
    other_user = _seed_report_user(UserRole.ADMIN)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/reports/generate", json={"report_type": "technical", "report_format": "html"})
        assert response.status_code == 201
    finally:
        _clear_overrides()

    other_client = _client_for(other_user)
    try:
        response = other_client.get("/api/v1/reports")
        assert response.status_code == 200
        assert response.json()["total"] == 0
    finally:
        _clear_overrides()
