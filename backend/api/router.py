from fastapi import APIRouter

from api.routes import auth, platform, status, tenants

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(status.router, tags=["status"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
