import io
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import app
from observability.logging import SafeJsonFormatter
from observability.tracing import configure_tracing


def test_metrics_endpoint_returns_prometheus_text() -> None:
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text


def test_http_metrics_increment_without_high_cardinality_labels() -> None:
    client = TestClient(app)
    client.get("/api/v1/status")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'route="/api/v1/status"' in response.text
    assert "tenant_id" not in response.text
    assert "user_id" not in response.text


def test_request_id_header_is_returned() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "phase-11-test"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "phase-11-test"


def test_existing_protected_endpoint_still_requires_auth() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/resources")

    assert response.status_code == 401


def test_safe_json_formatter_redacts_obvious_secret_fields() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeJsonFormatter())
    logger = logging.getLogger("observability-test")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.info("secret check", extra={"api_key": "sk-test", "access_token": "Bearer abc"})

    output = stream.getvalue()
    assert "sk-test" not in output
    assert "Bearer abc" not in output
    assert "[redacted]" in output


def test_tracing_initialization_can_be_disabled(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "otel_tracing_enabled", False)
    configure_tracing(FastAPI())
