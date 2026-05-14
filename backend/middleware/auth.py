from __future__ import annotations

from fastapi import Request


def request_tenant_id(request: Request):
    return getattr(request.state, "tenant_id", None)
