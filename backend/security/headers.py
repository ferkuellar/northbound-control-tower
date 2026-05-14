from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_body_bytes:
            from starlette.responses import JSONResponse

            return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        if request.method in {"POST", "PUT", "PATCH"} and request.url.path != "/metrics":
            content_type = request.headers.get("content-type", "")
            if content_type and "application/json" not in content_type:
                from starlette.responses import JSONResponse

                return JSONResponse(status_code=415, content={"detail": "Unsupported media type"})
        return await call_next(request)
