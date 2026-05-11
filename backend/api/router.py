from fastapi import APIRouter

from api.routes import platform, status

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(status.router, tags=["status"])
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
