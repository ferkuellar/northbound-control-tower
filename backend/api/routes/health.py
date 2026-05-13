from fastapi import APIRouter
from sqlalchemy import text

from core.database import engine
from core.redis import check_redis
from core.config import settings

router = APIRouter(prefix="/health")


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/db")
def database_health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {"status": "ok", "database": "reachable"}


@router.get("/redis")
def redis_health() -> dict[str, str]:
    check_redis()

    return {"status": "ok", "redis": "reachable"}


@router.get("/ready")
def ready() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    check_redis()

    return {"status": "ready"}


@router.get("/observability")
def observability_health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "observability_enabled": settings.observability_enabled,
        "prometheus_metrics_enabled": settings.prometheus_metrics_enabled,
        "otel_tracing_enabled": settings.otel_tracing_enabled,
    }
