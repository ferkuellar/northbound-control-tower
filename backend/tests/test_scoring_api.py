import uuid
from collections.abc import Generator

from fastapi.testclient import TestClient

from api.main import app
from auth.dependencies import get_current_user
from core.database import SessionLocal, get_db
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
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
    tenant = Tenant(name=f"Score API Tenant {suffix}", slug=f"score-api-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"score-{role.value.lower()}-{suffix}@northbound.local",
        full_name="Score API User",
        hashed_password="not-used",
        role=role.value,
        is_active=True,
    )
    cloud_account = CloudAccount(
        tenant_id=tenant.id,
        provider="aws",
        name="AWS Score API",
        auth_type="profile",
        default_region="us-east-1",
        is_active=True,
    )
    db.add_all([user, cloud_account])
    db.flush()
    score = CloudScore(
        tenant_id=tenant.id,
        cloud_account_id=None,
        provider=None,
        score_type="overall",
        score_value=100,
        grade="excellent",
        trend="unknown",
        summary="overall score is 100",
        evidence={"total_resources": 0, "total_findings": 0, "findings_by_severity": {}},
    )
    db.add(score)
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


def test_scores_require_auth() -> None:
    _clear_overrides()
    client = TestClient(app)

    response = client.get("/api/v1/scores/latest")

    assert response.status_code == 401


def test_viewer_can_read_scores() -> None:
    user = _seed_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.get("/api/v1/scores/latest")

        assert response.status_code == 200
        assert response.json()["items"]
    finally:
        _clear_overrides()


def test_viewer_cannot_calculate_scores() -> None:
    user = _seed_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/scores/calculate", json={})

        assert response.status_code == 403
    finally:
        _clear_overrides()


def test_analyst_can_calculate_scores() -> None:
    user = _seed_user(UserRole.ANALYST)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/scores/calculate", json={})

        assert response.status_code == 200
        assert len(response.json()["scores"]) == 6
    finally:
        _clear_overrides()


def test_score_summary_endpoint_works() -> None:
    user = _seed_user(UserRole.ADMIN)
    client = _client_for(user)
    try:
        response = client.get("/api/v1/scores/summary")

        assert response.status_code == 200
        assert response.json()["overall_score"] == 100
    finally:
        _clear_overrides()
