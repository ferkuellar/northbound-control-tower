import uuid

from core.database import SessionLocal
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.finding import Finding
from models.tenant import Tenant
from scoring.engine import RiskScoringEngine
from scoring.enums import ScoreType


def _seed_scope():
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Score Tenant {suffix}", slug=f"score-tenant-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    aws = CloudAccount(
        tenant_id=tenant.id,
        provider="aws",
        name="AWS Score",
        auth_type="profile",
        default_region="us-east-1",
        is_active=True,
    )
    oci = CloudAccount(
        tenant_id=tenant.id,
        provider="oci",
        name="OCI Score",
        auth_type="oci_config",
        default_region="us-ashburn-1",
        region="us-ashburn-1",
        is_active=True,
    )
    db.add_all([aws, oci])
    db.flush()
    findings = [
        Finding(
            tenant_id=tenant.id,
            cloud_account_id=aws.id,
            provider="aws",
            finding_type="public_exposure",
            category="security",
            severity="high",
            status="open",
            title="public",
            description="public",
            evidence={},
            recommendation="fix",
            rule_id="rule.public",
            fingerprint=f"{suffix}-public",
        ),
        Finding(
            tenant_id=tenant.id,
            cloud_account_id=aws.id,
            provider="aws",
            finding_type="missing_tags",
            category="governance",
            severity="medium",
            status="acknowledged",
            title="tags",
            description="tags",
            evidence={},
            recommendation="tag",
            rule_id="rule.tags",
            fingerprint=f"{suffix}-tags",
        ),
        Finding(
            tenant_id=tenant.id,
            cloud_account_id=oci.id,
            provider="oci",
            finding_type="unattached_volume",
            category="finops",
            severity="low",
            status="resolved",
            title="volume",
            description="volume",
            evidence={},
            recommendation="snapshot first",
            rule_id="rule.volume",
            fingerprint=f"{suffix}-volume",
        ),
    ]
    db.add_all(findings)
    db.commit()
    return db, tenant, aws, oci


def test_scoring_engine_calculates_and_persists_scores() -> None:
    db, tenant, _aws, _oci = _seed_scope()
    try:
        result = RiskScoringEngine(db).calculate(tenant_id=tenant.id)
        db.commit()

        assert len(result.scores) == 6
        assert db.query(CloudScore).filter(CloudScore.tenant_id == tenant.id).count() == 6
        security = next(score for score in result.scores if score.score_type == ScoreType.SECURITY_BASELINE.value)
        assert security.score_value == 85
    finally:
        db.close()


def test_scoring_engine_excludes_resolved_and_false_positive_findings() -> None:
    db, tenant, _aws, _oci = _seed_scope()
    try:
        result = RiskScoringEngine(db).calculate(tenant_id=tenant.id)
        finops = next(score for score in result.scores if score.score_type == ScoreType.FINOPS.value)

        assert finops.score_value == 100
    finally:
        db.close()


def test_scoring_engine_provider_and_cloud_account_filters_work() -> None:
    db, tenant, aws, _oci = _seed_scope()
    try:
        provider_result = RiskScoringEngine(db).calculate(tenant_id=tenant.id, provider="aws")
        account_result = RiskScoringEngine(db).calculate(tenant_id=tenant.id, cloud_account_id=aws.id)

        assert all(score.provider == "aws" for score in provider_result.scores)
        assert all(score.cloud_account_id == aws.id for score in account_result.scores)
    finally:
        db.close()


def test_scoring_engine_creates_history_and_trends() -> None:
    db, tenant, _aws, _oci = _seed_scope()
    try:
        first = RiskScoringEngine(db).calculate(tenant_id=tenant.id)
        db.commit()
        second = RiskScoringEngine(db).calculate(tenant_id=tenant.id)
        db.commit()

        assert len(first.scores) == 6
        assert len(second.scores) == 6
        assert db.query(CloudScore).filter(CloudScore.tenant_id == tenant.id).count() == 12
        assert all(score.trend in {"stable", "unknown"} for score in second.scores)
    finally:
        db.close()
