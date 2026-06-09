import uuid
from collections.abc import Generator

from fastapi.testclient import TestClient

from api.main import app
from auth.dependencies import get_current_user
from core.database import SessionLocal, get_db
from models.audit_log import AuditLog
from models.cloud_account import CloudAccount
from models.resource import Resource
from models.tenant import Tenant
from models.user import User, UserRole
from core.redis import redis_client


def _db_override() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_user(role: UserRole = UserRole.ADMIN) -> tuple[User, Resource, CloudAccount]:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"SaaS Tenant {suffix}", slug=f"saas-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"saas-{role.value.lower()}-{suffix}@northbound.local",
        full_name="SaaS User",
        hashed_password="not-used",
        role=role.value,
        is_active=True,
    )
    account = CloudAccount(
        tenant_id=tenant.id,
        provider="aws",
        name="AWS SaaS",
        auth_type="access_keys",
        access_key_id="AKIA_SHOULD_NOT_LEAK",
        secret_access_key="secret-should-not-leak",
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
        resource_id=f"i-{suffix}",
        fingerprint=suffix,
        name="saas-test",
        region="us-east-1",
        tags={},
        metadata_json={},
        relationships={},
    )
    audit = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        actor_user_id=user.id,
        actor_role=user.role,
        action="saas_test_event",
        resource_type="test",
        metadata_json={},
    )
    db.add_all([resource, audit])
    db.commit()
    db.refresh(user)
    db.refresh(resource)
    db.refresh(account)
    db.expunge(user)
    db.expunge(resource)
    db.expunge(account)
    db.close()
    return user, resource, account


def _client_for(user: User) -> TestClient:
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_security_headers_present() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_viewer_cannot_create_cloud_account() -> None:
    user, _, _ = _seed_user(UserRole.VIEWER)
    client = _client_for(user)
    try:
        response = client.post("/api/v1/cloud-accounts/aws", json={"name": "Denied", "auth_type": "profile"})

        assert response.status_code == 403
    finally:
        _clear_overrides()


def test_analyst_cannot_read_audit_logs() -> None:
    user, _, _ = _seed_user(UserRole.ANALYST)
    client = _client_for(user)
    try:
        response = client.get("/api/v1/audit/logs")

        assert response.status_code == 403
    finally:
        _clear_overrides()


def test_admin_can_read_audit_logs() -> None:
    user, _, _ = _seed_user(UserRole.ADMIN)
    client = _client_for(user)
    try:
        response = client.get("/api/v1/audit/logs")

        assert response.status_code == 200
        assert response.json()["total"] >= 1
    finally:
        _clear_overrides()


def test_cross_tenant_resource_access_is_blocked() -> None:
    user, _, _ = _seed_user(UserRole.ADMIN)
    _, other_resource, _ = _seed_user(UserRole.ADMIN)
    client = _client_for(user)
    try:
        response = client.get(f"/api/v1/resources/{other_resource.id}")

        assert response.status_code == 404
    finally:
        _clear_overrides()


def test_cloud_account_list_does_not_expose_secrets() -> None:
    user, _, _ = _seed_user(UserRole.ADMIN)
    client = _client_for(user)
    try:
        response = client.get("/api/v1/cloud-accounts")

        assert response.status_code == 200
        payload = response.text
        assert "secret-should-not-leak" not in payload
        assert "AKIA_SHOULD_NOT_LEAK" not in payload
    finally:
        _clear_overrides()


def test_login_rate_limit_returns_429() -> None:
    redis_client.delete("login:ip:testclient")
    client = TestClient(app)

    for _ in range(5):
        response = client.post("/api/v1/auth/login", json={"email": "missing@northbound.local", "password": "bad"})
        assert response.status_code == 401

    response = client.post("/api/v1/auth/login", json={"email": "missing@northbound.local", "password": "bad"})

    assert response.status_code == 429
    assert "Retry-After" in response.headers


# ── CORS header allowlist tests ───────────────────────────────────────────────

_CORS_ORIGIN = "http://localhost:3000"
_PREFLIGHT_BASE = {
    "Origin": _CORS_ORIGIN,
    "Access-Control-Request-Method": "GET",
}


def _preflight(header: str) -> str:
    """Return the Access-Control-Allow-Headers value for a preflight with the given request header."""
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={**_PREFLIGHT_BASE, "Access-Control-Request-Headers": header},
    )
    return response.headers.get("access-control-allow-headers", "")


def test_cors_allows_authorization_header() -> None:
    assert "authorization" in _preflight("Authorization").lower()


def test_cors_allows_content_type_header() -> None:
    assert "content-type" in _preflight("Content-Type").lower()


def test_cors_allows_x_tenant_id_header() -> None:
    assert "x-tenant-id" in _preflight("X-Tenant-ID").lower()


def test_cors_allows_x_request_id_header() -> None:
    assert "x-request-id" in _preflight("X-Request-ID").lower()


def test_cors_allows_accept_header() -> None:
    assert "accept" in _preflight("Accept").lower()


def test_cors_does_not_use_wildcard_headers() -> None:
    import api.main as main_module
    import inspect

    source = inspect.getsource(main_module)
    assert 'allow_headers=["*"]' not in source
    assert "allow_headers=['*']" not in source
