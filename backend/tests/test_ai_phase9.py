import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from ai.context_builder import AIContextBuilder
from ai.enums import AIProvider
from ai.errors import AIOutputValidationError
from ai.prompts import full_assessment_prompt
from ai.schemas import AIProviderStatus
from ai.validators import validate_ai_output
from api.main import app
from auth.dependencies import get_current_user
from core.database import SessionLocal, get_db
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from models.user import User, UserRole


def _db_override() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_ai_user(role: UserRole = UserRole.ADMIN) -> User:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"AI Tenant {suffix}", slug=f"ai-tenant-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"ai-{role.value.lower()}-{suffix}@northbound.local",
        full_name="AI User",
        hashed_password="not-used",
        role=role.value,
        is_active=True,
    )
    account = CloudAccount(
        tenant_id=tenant.id,
        provider="aws",
        name="AWS AI",
        auth_type="profile",
        access_key_id="AKIA_SHOULD_NOT_APPEAR",
        secret_access_key="secret-should-not-appear",
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
        resource_id="i-ai-test",
        fingerprint=uuid.uuid4().hex,
        name="ai-test-instance",
        region="us-east-1",
        lifecycle_status="running",
        exposure_level="public",
        environment="prod",
        tags={"owner": "platform"},
        metadata_json={"private_key": "-----BEGIN PRIVATE KEY-----bad-----END PRIVATE KEY-----", "cpu_count": 2},
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
        evidence={"secret_access_key": "do-not-include", "public_ip": "203.0.113.10"},
        recommendation="Validate exposure before making changes.",
        rule_id="public_exposure_v1",
        fingerprint=uuid.uuid4().hex,
    )
    score = CloudScore(
        tenant_id=tenant.id,
        cloud_account_id=None,
        provider=None,
        score_type="overall",
        score_value=70,
        grade="fair",
        trend="unknown",
        summary="overall score is 70",
        evidence={"total_findings": 1},
    )
    db.add_all([resource, finding, score])
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


class FakeAIProvider:
    provider_name = "deepseek"
    model_name = "fake-model"

    def health_check(self) -> AIProviderStatus:
        return AIProviderStatus(
            provider=AIProvider.DEEPSEEK,
            configured=True,
            enabled=True,
            model_name=self.model_name,
            message="configured",
        )

    def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str:
        assert "Use only the provided context" in prompt
        return (
            '{"executive_summary":"Public exposure requires validation.",'
            '"limitations":["Analysis is limited to provided context."],'
            '"remediation_recommendations":["Validate approval, backup, snapshot, and rollback before delete actions."]}'
        )


def test_context_builder_sanitizes_secrets_and_includes_summaries() -> None:
    user = _seed_ai_user()
    db = SessionLocal()
    try:
        context = AIContextBuilder(db).build(tenant_id=user.tenant_id)
        serialized = str(context)

        assert context["scores"]["overall"] == 70
        assert context["findings_summary"]["total_open"] == 1
        assert context["inventory_summary"]["total_resources"] == 1
        assert "secret-should-not-appear" not in serialized
        assert "PRIVATE KEY" not in serialized
        assert "do-not-include" not in serialized
    finally:
        db.close()


def test_prompt_template_includes_safety_instructions() -> None:
    prompt = full_assessment_prompt({"limitations": {"resources_available": False}})

    assert "Do not invent resources" in prompt
    assert "approval, backup, snapshot, and rollback" in prompt


def test_validator_blocks_credentials_and_executed_claims() -> None:
    context = {"limitations": {"resources_available": True}, "scope": {"provider": "aws"}, "inventory_summary": {"by_provider": {"aws": 1}}}

    with pytest.raises(AIOutputValidationError):
        validate_ai_output("-----BEGIN PRIVATE KEY-----bad", context=context)
    with pytest.raises(AIOutputValidationError):
        validate_ai_output("I deleted the public instance.", context=context)


def test_viewer_cannot_generate_ai_analysis() -> None:
    user = _seed_ai_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/ai/analyze", json={"analysis_type": "full_assessment", "provider": "deepseek"})

        assert response.status_code == 403
    finally:
        _clear_overrides()


def test_context_preview_is_sanitized() -> None:
    user = _seed_ai_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.get("/api/v1/ai/context-preview")

        assert response.status_code == 200
        assert "secret-should-not-appear" not in response.text
        assert "PRIVATE KEY" not in response.text
    finally:
        _clear_overrides()


def test_analyst_can_generate_ai_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _seed_ai_user(UserRole.ANALYST)
    monkeypatch.setattr("ai.service.get_ai_provider", lambda provider=None: FakeAIProvider())
    client = _client_for(user)
    try:
        response = client.post("/api/v1/ai/analyze", json={"analysis_type": "full_assessment", "provider": "deepseek"})

        assert response.status_code == 201
        body = response.json()["analysis"]
        assert body["status"] == "completed"
        assert body["ai_provider"] == "deepseek"
        assert body["output"]["executive_summary"]
    finally:
        _clear_overrides()


def test_ai_analysis_list_is_tenant_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _seed_ai_user(UserRole.ADMIN)
    other_user = _seed_ai_user(UserRole.ADMIN)
    monkeypatch.setattr("ai.service.get_ai_provider", lambda provider=None: FakeAIProvider())
    client = _client_for(user)
    try:
        create_response = client.post("/api/v1/ai/analyze", json={"analysis_type": "full_assessment", "provider": "deepseek"})
        assert create_response.status_code == 201
    finally:
        _clear_overrides()

    other_client = _client_for(other_user)
    try:
        response = other_client.get("/api/v1/ai/analyses")

        assert response.status_code == 200
        assert response.json()["total"] == 0
    finally:
        _clear_overrides()
