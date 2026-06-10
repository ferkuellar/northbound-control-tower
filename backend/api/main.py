from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from api.routes import health
from cloud_shell.router import router as cloud_shell_router
from core.config import settings
from core.errors import register_exception_handlers
from core.logging import configure_logging
from middleware.rate_limit import RateLimitMiddleware
from middleware.tenant import TenantContextMiddleware
from observability.metrics import metrics_response
from observability.middleware import PrometheusHTTPMetricsMiddleware, RequestIdMiddleware
from observability.tracing import configure_tracing
from security.headers import RequestValidationMiddleware, SecurityHeadersMiddleware


_UNSAFE_JWT_SECRET = "change-me-only-for-local-development"
_UNSAFE_JWT_SECRETS = {
    _UNSAFE_JWT_SECRET,
    "change-this-local-development-secret",
}
_WEAK_DATABASE_URL = "postgresql+psycopg://nct:nct_dev_password@postgres:5432/nct"


def _validate_production_secrets() -> None:
    if settings.app_env != "production":
        return
    if settings.jwt_secret_key in _UNSAFE_JWT_SECRETS:
        raise RuntimeError(
            "JWT_SECRET_KEY is the default insecure value. "
            "Set a strong secret before running in production."
        )
    if not settings.credential_encryption_key:
        raise RuntimeError(
            "CREDENTIAL_ENCRYPTION_KEY is not set. "
            "Generate a Fernet key and set it before running in production."
        )
    if settings.database_url == _WEAK_DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL contains the default development password. "
            "Set a strong POSTGRES_PASSWORD and update DATABASE_URL before running in production."
        )
    if not settings.oci_vault_id:
        raise RuntimeError(
            "Production secrets must come from a cloud secret provider. "
            "Set OCI_VAULT_ID before running in production."
        )
    if "localhost" in settings.backend_cors_origins_raw.lower():
        raise RuntimeError(
            "BACKEND_CORS_ORIGINS contains localhost in production. "
            "Set the actual domain(s)."
        )


def create_app() -> FastAPI:
    configure_logging()
    _validate_production_secrets()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Northbound Control Tower modular monolith API.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Tenant-ID",
            "X-Request-ID",
            "Accept",
        ],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(PrometheusHTTPMetricsMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    app.include_router(health.router, tags=["health"])
    app.include_router(cloud_shell_router)
    app.include_router(api_router)
    if settings.observability_enabled and settings.prometheus_metrics_enabled:
        app.add_route("/metrics", metrics_response, methods=["GET"])
    configure_tracing(app)

    return app


app = create_app()
