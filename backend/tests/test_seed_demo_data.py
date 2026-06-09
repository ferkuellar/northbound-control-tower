"""Tests for the seed_demo_data script."""

from sqlalchemy import select

from core.database import SessionLocal
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from models.user import User
from scripts.seed_demo_data import _DEMO_PASSWORD, seed


def test_seed_creates_tenant() -> None:
    before = _count(Tenant)
    seed()
    assert _count(Tenant) == before + 1


def test_seed_creates_admin_user() -> None:
    seed()
    db = SessionLocal()
    try:
        users = db.scalars(
            select(User).where(User.email.like("%@demo.northbound.local"))
        ).all()
        assert any(u.role == "ADMIN" for u in users)
    finally:
        db.close()


def test_seed_password_is_hashed() -> None:
    seed()
    db = SessionLocal()
    try:
        user = db.scalars(
            select(User).where(User.email.like("%@demo.northbound.local"))
        ).first()
        assert user is not None
        assert user.hashed_password != _DEMO_PASSWORD
        assert user.hashed_password.startswith("$2b$")
    finally:
        db.close()


def test_seed_creates_resources() -> None:
    before = _count(Resource)
    seed()
    assert _count(Resource) >= before + 2


def test_seed_creates_findings() -> None:
    before = _count(Finding)
    seed()
    assert _count(Finding) >= before + 3


def test_seed_creates_cloud_scores() -> None:
    before = _count(CloudScore)
    seed()
    assert _count(CloudScore) >= before + 3


def test_seed_runs_twice_without_collision() -> None:
    seed()
    seed()


def _count(model) -> int:
    db = SessionLocal()
    try:
        return db.query(model).count()
    finally:
        db.close()
