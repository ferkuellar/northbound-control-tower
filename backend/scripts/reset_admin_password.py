import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from auth.security import hash_password
from core.config import settings
from core.database import SessionLocal
from models.tenant import Tenant, TenantStatus
from models.user import User


DEFAULT_EMAIL = "admin@northbound.local"
DEFAULT_FULL_NAME = "Northbound Admin"
DEFAULT_TENANT_NAME = "Northbound Demo"
DEFAULT_TENANT_SLUG = "northbound-demo"


def _validate_password(password: str) -> None:
    if len(password) < settings.password_min_length:
        raise ValueError(f"Password must be at least {settings.password_min_length} characters long")
    if len(password) > 128:
        raise ValueError("Password must be at most 128 characters long")
    if not any(character.isdigit() for character in password):
        raise ValueError("Password must contain at least one number")
    if not any(character.isalpha() for character in password):
        raise ValueError("Password must contain at least one letter")


def main() -> int:
    email = os.environ.get("NCT_ADMIN_EMAIL", DEFAULT_EMAIL).lower()
    full_name = os.environ.get("NCT_ADMIN_FULL_NAME", DEFAULT_FULL_NAME)
    tenant_name = os.environ.get("NCT_TENANT_NAME", DEFAULT_TENANT_NAME)
    tenant_slug = os.environ.get("NCT_TENANT_SLUG", DEFAULT_TENANT_SLUG)
    password = os.environ.get("NCT_ADMIN_PASSWORD")

    if not password:
        print("Set NCT_ADMIN_PASSWORD before running this script.", file=sys.stderr)
        return 2

    try:
        _validate_password(password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            existing_users = db.scalar(select(func.count()).select_from(User))
            if existing_users:
                print(f"User not found: {email}", file=sys.stderr)
                return 1

            tenant = Tenant(
                name=tenant_name,
                slug=tenant_slug,
                status=TenantStatus.ACTIVE.value,
            )
            db.add(tenant)
            db.flush()

            user = User(
                tenant_id=tenant.id,
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                role="ADMIN",
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"Admin user created for {email}")
            return 0

        user.hashed_password = hash_password(password)
        user.is_active = True
        db.commit()

    print(f"Password reset for {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
