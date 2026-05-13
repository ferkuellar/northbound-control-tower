from __future__ import annotations

import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from core.config import settings
from core.database import engine

logger = logging.getLogger(__name__)
_configured = False


def configure_tracing(app: FastAPI) -> None:
    global _configured
    if _configured or not settings.observability_enabled or not settings.otel_tracing_enabled:
        return
    try:
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": settings.otel_service_name,
                    "deployment.environment": settings.app_env,
                }
            )
        )
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument(engine=engine)
        RedisInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        _configured = True
    except Exception:
        logger.exception("OpenTelemetry tracing initialization failed")
