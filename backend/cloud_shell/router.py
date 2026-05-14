from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from auth.security import decode_access_token
from cloud_shell.command_executor import CloudShellExecutor
from cloud_shell.schemas import ShellUserContext
from core.database import SessionLocal
from models.user import User

router = APIRouter()


def _token_from_protocol_header(header_value: str | None) -> str | None:
    if not header_value:
        return None
    parts = [part.strip() for part in header_value.split(",")]
    for part in parts:
        if part and part != "northbound":
            return part
    return None


def _authenticate_websocket(websocket: WebSocket, db) -> User | None:
    token = _token_from_protocol_header(websocket.headers.get("sec-websocket-protocol"))
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload.get("sub")))
        token_tenant_id = uuid.UUID(str(payload.get("tenant_id"))) if payload.get("tenant_id") else None
    except (TypeError, ValueError):
        return None

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        return None
    if token_tenant_id and token_tenant_id != user.tenant_id:
        return None
    return user


@router.websocket("/ws/cloud-shell")
async def cloud_shell_websocket(websocket: WebSocket) -> None:
    await websocket.accept(subprotocol="northbound")
    db = SessionLocal()
    try:
        user = _authenticate_websocket(websocket, db)
        if user is None:
            await websocket.send_json({"status": "error", "output": "Authentication required.", "metadata": {}})
            await websocket.close(code=1008)
            return

        user_context = ShellUserContext(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role,
            source_ip=websocket.client.host if websocket.client else None,
            user_agent=websocket.headers.get("user-agent"),
        )
        executor = CloudShellExecutor()
        await websocket.send_text("Northbound Cloud Shell\nControlled Operations Console\n\nType: nb help")

        while True:
            raw_command = await websocket.receive_text()
            response = executor.execute(db, raw_command=raw_command, user_context=user_context)
            await websocket.send_json(response.model_dump())
    except WebSocketDisconnect:
        return
    finally:
        db.close()

