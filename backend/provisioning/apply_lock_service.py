from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningExecutionLock, ProvisioningRequest

LOCK_TTL_MINUTES = 30


@dataclass(frozen=True)
class LockResult:
    acquired: bool
    lock: ProvisioningExecutionLock | None
    reason: str | None = None


class ApplyLockService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def acquire(self, request: ProvisioningRequest, *, locked_by: str | None = None) -> LockResult:
        now = datetime.now(UTC)
        active = self.db.scalar(
            select(ProvisioningExecutionLock)
            .where(ProvisioningExecutionLock.request_id == request.id)
            .where(ProvisioningExecutionLock.status == "ACTIVE")
            .where(ProvisioningExecutionLock.released_at.is_(None))
            .order_by(ProvisioningExecutionLock.locked_at.desc())
        )
        if active and active.expires_at > now:
            return LockResult(False, active, "Another apply is already running for this request.")
        if active and active.expires_at <= now:
            active.status = "EXPIRED"
            active.released_at = now
            active.error_message = "Lock expired before release."
            self.db.flush()

        lock = ProvisioningExecutionLock(
            request_id=request.id,
            lock_token=f"apply-{uuid.uuid4().hex}",
            locked_by=uuid.UUID(str(locked_by)) if locked_by else None,
            locked_at=now,
            expires_at=now + timedelta(minutes=LOCK_TTL_MINUTES),
            released_at=None,
            status="ACTIVE",
        )
        self.db.add(lock)
        self.db.flush()
        return LockResult(True, lock)

    def release(self, lock: ProvisioningExecutionLock, *, status: str = "RELEASED", error_message: str | None = None) -> None:
        lock.status = status
        lock.released_at = datetime.now(UTC)
        lock.error_message = error_message
        self.db.flush()
