from fastapi import APIRouter

from api.routes import (
    admin_tenants,
    ai,
    audit,
    auth,
    cloud_accounts,
    cost_optimization,
    dashboard,
    findings,
    inventory,
    platform,
    provisioning,
    reports,
    resources,
    scores,
    status,
    tenants,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(status.router, tags=["status"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(admin_tenants.router, prefix="/admin/tenants", tags=["admin-tenants"])
api_router.include_router(cloud_accounts.router, prefix="/cloud-accounts", tags=["cloud-accounts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(cost_optimization.router, prefix="/cost-optimization", tags=["cost-optimization"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(scores.router, prefix="/scores", tags=["scores"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
api_router.include_router(provisioning.router, prefix="/provisioning", tags=["provisioning"])
