from fastapi import APIRouter

from core.config import settings

router = APIRouter()


@router.get("/status")
def get_status() -> dict[str, bool | str]:
    return {
        "success": True,
        "service": "backend",
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "architecture": "modular_monolith",
    }
