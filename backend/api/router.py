from fastapi import APIRouter

from api.routes import auth, cloud_accounts, findings, inventory, platform, resources, scores, status, tenants

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(status.router, tags=["status"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(cloud_accounts.router, prefix="/cloud-accounts", tags=["cloud-accounts"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(scores.router, prefix="/scores", tags=["scores"])
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
