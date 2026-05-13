from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from observability.logging import set_request_id
from observability.metrics import (
    HTTP_EXCEPTIONS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)

logger = logging.getLogger("observability.http")


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return str(path)
    return request.url.path


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class PrometheusHTTPMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method
        route = "unresolved"
        if request.url.path.startswith("/metrics"):
            return await call_next(request)

        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=route).inc()
        started = time.perf_counter()
        status_code = "500"
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception:
            HTTP_EXCEPTIONS_TOTAL.labels(method=method, route=route).inc()
            logger.exception(
                "http_request_failed",
                extra={
                    "method": method,
                    "route": route_template(request),
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            raise
        finally:
            resolved_route = route_template(request)
            duration = time.perf_counter() - started
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=route).dec()
            HTTP_REQUESTS_TOTAL.labels(method=method, route=resolved_route, status_code=status_code).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=resolved_route, status_code=status_code).observe(duration)
            logger.info(
                "http_request_completed",
                extra={
                    "method": method,
                    "route": resolved_route,
                    "status": status_code,
                    "duration_ms": int(duration * 1000),
                },
            )
