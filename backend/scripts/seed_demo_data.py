"""
Seed demo data for local AI context testing.

Creates a tenant, admin user, AWS cloud account, resources, findings, and
cloud scores so that AIContextBuilder returns a non-empty context during
Claude smoke tests and end-to-end demos.

Usage:
    docker compose run --rm backend python scripts/seed_demo_data.py

IMPORTANT: This script is for local/dev/demo environments only.
           Never run against production. Never promote demo data to production.
           DemoPass123! is a demo-only credential — do not reuse.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth.security import hash_password
from core.database import SessionLocal
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from models.user import User


_DEMO_PASSWORD = "DemoPass123!"


def seed() -> None:
    db = SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:6]
        demo_email = f"admin-{suffix}@demo.northbound.local"

        # ── Tenant ────────────────────────────────────────────────────────────
        tenant = Tenant(
            name="Demo Corp",
            slug=f"demo-{suffix}",
            status="active",
            industry="Technology",
            contact_name="Demo Admin",
            contact_email=demo_email,
        )
        db.add(tenant)
        db.flush()

        # ── User ──────────────────────────────────────────────────────────────
        user = User(
            tenant_id=tenant.id,
            email=demo_email,
            full_name="Demo Admin",
            hashed_password=hash_password(_DEMO_PASSWORD),
            role="ADMIN",
            is_active=True,
        )
        db.add(user)

        # ── Cloud account ─────────────────────────────────────────────────────
        account = CloudAccount(
            tenant_id=tenant.id,
            provider="aws",
            name="AWS Production",
            account_id="123456789012",
            auth_type="role_arn",
            role_arn="arn:aws:iam::123456789012:role/northbound-readonly",
            default_region="us-east-1",
            is_active=True,
        )
        db.add(account)
        db.flush()

        # ── Resources ─────────────────────────────────────────────────────────
        r1 = Resource(
            tenant_id=tenant.id,
            cloud_account_id=account.id,
            provider="aws",
            resource_type="compute",
            resource_id=f"i-{uuid.uuid4().hex[:8]}",
            fingerprint=uuid.uuid4().hex,
            name="web-server-prod",
            region="us-east-1",
            lifecycle_status="running",
            exposure_level="public",
            environment="prod",
            criticality="high",
            metadata_json={"instance_type": "t3.medium", "ami": "ami-0abcdef1234567890"},
            tags={},
            relationships={},
        )

        r2 = Resource(
            tenant_id=tenant.id,
            cloud_account_id=account.id,
            provider="aws",
            resource_type="block_storage",
            resource_id=f"vol-{uuid.uuid4().hex[:8]}",
            fingerprint=uuid.uuid4().hex,
            name="data-volume",
            region="us-east-1",
            lifecycle_status="in-use",
            exposure_level="private",
            environment="prod",
            criticality="high",
            metadata_json={"encrypted": False, "size_gb": 500, "volume_type": "gp3"},
            tags={},
            relationships={},
        )

        db.add_all([r1, r2])
        db.flush()

        # ── Findings ──────────────────────────────────────────────────────────
        db.add_all([
            Finding(
                tenant_id=tenant.id,
                cloud_account_id=account.id,
                resource_id=r1.id,
                provider="aws",
                finding_type="public_exposure",
                category="security",
                severity="high",
                status="open",
                title="EC2 instance publicly accessible without WAF",
                description=(
                    "web-server-prod has a public IP with port 443 exposed directly "
                    "to the internet and no WAF attached."
                ),
                recommendation=(
                    "Attach WAF or restrict via ALB + security group. "
                    "Requires approval, backup, snapshot, and rollback validation."
                ),
                evidence={"exposure_level": "public", "public_ip": "52.10.11.12", "open_ports": [443, 22]},
                rule_id="aws-ec2-public-exposure",
                fingerprint=uuid.uuid4().hex,
            ),
            Finding(
                tenant_id=tenant.id,
                cloud_account_id=account.id,
                resource_id=r2.id,
                provider="aws",
                finding_type="unencrypted_storage",
                category="security",
                severity="high",
                status="open",
                title="EBS volume not encrypted at rest",
                description=(
                    "data-volume (500 GB, gp3) has encryption disabled. "
                    "Any snapshot or cross-account share exposes data in plaintext."
                ),
                recommendation=(
                    "Enable EBS encryption via snapshot copy workflow. "
                    "Requires approval, backup, and rollback validation."
                ),
                evidence={"encrypted": False, "size_gb": 500, "volume_type": "gp3"},
                rule_id="aws-ebs-unencrypted",
                fingerprint=uuid.uuid4().hex,
            ),
            Finding(
                tenant_id=tenant.id,
                cloud_account_id=account.id,
                resource_id=r1.id,
                provider="aws",
                finding_type="missing_tags",
                category="governance",
                severity="medium",
                status="open",
                title="Resource missing required governance tags",
                description=(
                    "web-server-prod is missing mandatory tags: owner, cost_center, application. "
                    "Cost allocation and ownership tracking are impacted."
                ),
                recommendation="Apply standard tagging workflow using the governance runbook.",
                evidence={"missing_tags": ["owner", "cost_center", "application"]},
                rule_id="aws-resource-missing-tags",
                fingerprint=uuid.uuid4().hex,
            ),
        ])

        # ── Cloud scores ──────────────────────────────────────────────────────
        db.add_all([
            CloudScore(
                tenant_id=tenant.id,
                cloud_account_id=account.id,
                provider="aws",
                score_type="security_baseline",
                score_value=42,
                grade="D",
                trend="stable",
                summary=(
                    "Security baseline score is critical due to public EC2 exposure "
                    "and unencrypted EBS volume. Immediate remediation required."
                ),
                evidence={"open_findings": 2, "critical": 0, "high": 2},
            ),
            CloudScore(
                tenant_id=tenant.id,
                cloud_account_id=account.id,
                provider="aws",
                score_type="governance",
                score_value=55,
                grade="C",
                trend="stable",
                summary=(
                    "Governance score is below target. Missing tags on production "
                    "resources prevent cost allocation and ownership tracking."
                ),
                evidence={"open_findings": 3, "missing_tag_resources": 1},
            ),
            CloudScore(
                tenant_id=tenant.id,
                cloud_account_id=account.id,
                provider="aws",
                score_type="overall",
                score_value=49,
                grade="D",
                trend="stable",
                summary=(
                    "Overall cloud health score is below acceptable threshold. "
                    "Security and governance findings are the primary drivers. "
                    "Prioritize encryption and WAF deployment."
                ),
                evidence={"open_findings": 3, "high": 2, "medium": 1},
            ),
        ])

        db.commit()

        print(f"\nTenant: {tenant.id}")
        print(f"Login:  {demo_email} / {_DEMO_PASSWORD}")
        print("Test:   POST /api/v1/ai/analyze")
        print('        {"analysis_type": "executive_summary", "provider": "claude"}')
        print()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
