from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth.security import decode_access_token
from core.config import settings
from security.rate_limit import rate_limiter

logger = logging.getLogger("security.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rule = self._rule_for(request)
        if rule is None:
            return await call_next(request)
        key, limit, window_seconds = rule
        decision = rate_limiter.check(key, limit=limit, window_seconds=window_seconds)
        if not decision.allowed:
            logger.warning("rate_limit_exceeded", extra={"route": request.url.path, "limit": limit, "window_seconds": window_seconds})
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(decision.retry_after)},
            )
        return await call_next(request)

    def _rule_for(self, request: Request) -> tuple[str, int, int] | None:
        if request.method not in {"POST", "PATCH", "PUT"}:
            return None
        path = request.url.path
        ip = request.client.host if request.client else "unknown"
        user_id, tenant_id = self._claims(request)
        if path == "/api/v1/auth/login":
            return f"login:ip:{ip}", settings.rate_limit_login_per_minute, 60
        if path == "/api/v1/ai/analyze":
            return f"ai:user:{user_id or ip}", settings.rate_limit_ai_per_minute, 60
        if path == "/api/v1/reports/generate":
            return f"reports:user:{user_id or ip}", settings.rate_limit_reports_per_minute, 60
        if "/api/v1/inventory/" in path and "/scan/" in path:
            return f"inventory:tenant:{tenant_id or ip}", settings.rate_limit_inventory_scan_per_minute, 60
        return None

    def _claims(self, request: Request) -> tuple[str | None, str | None]:
        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return None, None
        try:
            payload = decode_access_token(authorization.split(" ", 1)[1])
        except ValueError:
            return None, None
        return str(payload.get("sub")) if payload.get("sub") else None, str(payload.get("tenant_id")) if payload.get("tenant_id") else None
