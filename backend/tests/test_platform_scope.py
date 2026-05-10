from fastapi.testclient import TestClient

from api.main import app


def test_platform_scope_is_phase0_limited() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/platform/scope")

    assert response.status_code == 200
    payload = response.json()
    assert payload["clouds"] == ["aws", "oci"]
    assert payload["architecture"] == "modular_monolith"
    assert "idle_compute" in payload["findings"]
    assert "public_exposure" in payload["findings"]
