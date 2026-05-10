from fastapi import APIRouter
from sqlalchemy import text

from core.database import engine
from core.redis import redis_client

router = APIRouter(prefix="/health")


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready")
def ready() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    redis_client.ping()

    return {"status": "ready"}
