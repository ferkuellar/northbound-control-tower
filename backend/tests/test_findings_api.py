import uuid
from collections.abc import Generator

from fastapi.testclient import TestClient

from api.main import app
from auth.dependencies import get_current_user
from core.database import SessionLocal, get_db
from findings.enums import FindingStatus
from models.cloud_account import CloudAccount
from models.finding import Finding
from models.tenant import Tenant
from models.user import User, UserRole


def _db_override() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_user(role: UserRole = UserRole.ADMIN):
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"API Tenant {suffix}", slug=f"api-tenant-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"{role.value.lower()}-{suffix}@northbound.local",
        full_name="API User",
        hashed_password="not-used",
        role=role.value,
        is_active=True,
    )
    cloud_account = CloudAccount(
        tenant_id=tenant.id,
        provider="aws",
        name="AWS API",
        auth_type="profile",
        default_region="us-east-1",
        is_active=True,
    )
    db.add_all([user, cloud_account])
    db.flush()
    finding = Finding(
        tenant_id=tenant.id,
        cloud_account_id=cloud_account.id,
        provider="aws",
        finding_type="missing_tags",
        category="governance",
        severity="medium",
        status="open",
        title="Missing tags",
        description="Resource is missing tags.",
        evidence={},
        recommendation="Add required tags.",
        rule_id="test.rule",
        fingerprint=uuid.uuid4().hex,
    )
    db.add(finding)
    db.commit()
    db.refresh(user)
    db.refresh(finding)
    db.expunge(user)
    db.expunge(finding)
    db.close()
    return user, finding


def _client_for(user: User) -> TestClient:
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_findings_list_requires_auth() -> None:
    _clear_overrides()
    client = TestClient(app)

    response = client.get("/api/v1/findings")

    assert response.status_code == 401


def test_viewer_can_read_findings() -> None:
    user, _finding = _seed_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.get("/api/v1/findings")

        assert response.status_code == 200
        assert response.json()["total"] == 1
    finally:
        _clear_overrides()


def test_viewer_cannot_run_findings() -> None:
    user, _finding = _seed_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/findings/run", json={})

        assert response.status_code == 403
    finally:
        _clear_overrides()


def test_analyst_can_run_findings() -> None:
    user, _finding = _seed_user(UserRole.ANALYST)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/findings/run", json={})

        assert response.status_code == 200
        assert response.json()["resources_evaluated"] == 0
    finally:
        _clear_overrides()


def test_admin_can_update_finding_status() -> None:
    user, finding = _seed_user(UserRole.ADMIN)
    client = _client_for(user)
    try:
        response = client.patch(f"/api/v1/findings/{finding.id}/status", json={"status": FindingStatus.ACKNOWLEDGED.value})

        assert response.status_code == 200
        assert response.json()["status"] == FindingStatus.ACKNOWLEDGED.value
    finally:
        _clear_overrides()
