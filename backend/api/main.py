from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from api.routes import health
from core.config import settings
from core.errors import register_exception_handlers
from core.logging import configure_logging
from middleware.rate_limit import RateLimitMiddleware
from middleware.tenant import TenantContextMiddleware
from observability.metrics import metrics_response
from observability.middleware import PrometheusHTTPMetricsMiddleware, RequestIdMiddleware
from observability.tracing import configure_tracing
from security.headers import RequestValidationMiddleware, SecurityHeadersMiddleware


def create_app() -> FastAPI:
    configure_logging()

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
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(PrometheusHTTPMetricsMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    app.include_router(health.router, tags=["health"])
    app.include_router(api_router)
    if settings.observability_enabled and settings.prometheus_metrics_enabled:
        app.add_route("/metrics", metrics_response, methods=["GET"])
    configure_tracing(app)

    return app


app = create_app()
