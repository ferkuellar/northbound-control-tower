import uuid

from core.database import SessionLocal
from findings.engine import FindingsEngine
from models.cloud_account import CloudAccount
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant


def _create_scope():
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Tenant {suffix}", slug=f"tenant-{suffix}", status="active")
    other_tenant = Tenant(name=f"Other {suffix}", slug=f"other-{suffix}", status="active")
    db.add_all([tenant, other_tenant])
    db.flush()
    cloud_account = CloudAccount(
        tenant_id=tenant.id,
        provider="aws",
        name="AWS Test",
        auth_type="profile",
        default_region="us-east-1",
        is_active=True,
    )
    oci_account = CloudAccount(
        tenant_id=tenant.id,
        provider="oci",
        name="OCI Test",
        auth_type="oci_config",
        default_region="us-ashburn-1",
        region="us-ashburn-1",
        is_active=True,
    )
    db.add_all([cloud_account, oci_account])
    db.flush()
    resources = [
        Resource(
            tenant_id=tenant.id,
            cloud_account_id=cloud_account.id,
            provider="aws",
            resource_type="compute",
            resource_id=f"i-{suffix}",
            name="app",
            region="us-east-1",
            raw_type="AWS::EC2::Instance",
            lifecycle_status="running",
            exposure_level="private",
            environment="prod",
            metadata_json={},
            tags={},
            relationships={},
        ),
        Resource(
            tenant_id=tenant.id,
            cloud_account_id=oci_account.id,
            provider="oci",
            resource_type="block_storage",
            resource_id=f"ocid1.volume.{suffix}",
            name="volume",
            region="us-ashburn-1",
            raw_type="OCI::Core::Volume",
            lifecycle_status="available",
            exposure_level="private",
            environment="dev",
            metadata_json={},
            tags={},
            relationships={},
        ),
        Resource(
            tenant_id=other_tenant.id,
            cloud_account_id=cloud_account.id,
            provider="aws",
            resource_type="compute",
            resource_id=f"other-{suffix}",
            name="other",
            region="us-east-1",
            raw_type="AWS::EC2::Instance",
            lifecycle_status="running",
            exposure_level="public",
            environment="unknown",
            metadata_json={},
            tags={},
            relationships={},
        ),
    ]
    db.add_all(resources)
    db.commit()
    return db, tenant, cloud_account, oci_account, resources


def test_findings_engine_runs_over_mixed_aws_oci_resources() -> None:
    db, tenant, _cloud_account, _oci_account, _resources = _create_scope()
    try:
        summary = FindingsEngine(db).run(tenant_id=tenant.id)
        db.commit()

        assert summary.resources_evaluated == 2
        assert summary.findings_created >= 2
        assert "missing_tags" in summary.findings_by_type
        assert db.query(Finding).filter(Finding.tenant_id == tenant.id).count() >= 2
    finally:
        db.close()


def test_findings_engine_uses_deterministic_fingerprint_and_no_duplicates() -> None:
    db, tenant, cloud_account, _oci_account, resources = _create_scope()
    try:
        engine = FindingsEngine(db)
        first = engine.run(tenant_id=tenant.id, cloud_account_id=cloud_account.id)
        db.commit()
        count_after_first = db.query(Finding).filter(Finding.tenant_id == tenant.id).count()

        second = engine.run(tenant_id=tenant.id, cloud_account_id=cloud_account.id)
        db.commit()
        count_after_second = db.query(Finding).filter(Finding.tenant_id == tenant.id).count()

        assert engine.fingerprint(resources[0], engine.registry.rules()[0]) == engine.fingerprint(resources[0], engine.registry.rules()[0])
        assert first.findings_created > 0
        assert second.findings_updated > 0
        assert count_after_first == count_after_second
    finally:
        db.close()


def test_findings_engine_enforces_tenant_scope() -> None:
    db, tenant, _cloud_account, _oci_account, _resources = _create_scope()
    try:
        summary = FindingsEngine(db).run(tenant_id=tenant.id)

        assert summary.resources_evaluated == 2
    finally:
        db.close()
