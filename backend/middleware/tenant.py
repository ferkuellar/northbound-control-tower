from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth.security import decode_access_token


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.tenant_id = None
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1]
            try:
                payload = decode_access_token(token)
                tenant_id = payload.get("tenant_id")
                if tenant_id:
                    request.state.tenant_id = uuid.UUID(str(tenant_id))
                    requested_tenant = request.headers.get("X-Tenant-ID")
                    if requested_tenant and uuid.UUID(requested_tenant) != request.state.tenant_id:
                        return JSONResponse(status_code=403, content={"detail": "Tenant mismatch"})
            except (ValueError, TypeError):
                request.state.tenant_id = None
        return await call_next(request)
