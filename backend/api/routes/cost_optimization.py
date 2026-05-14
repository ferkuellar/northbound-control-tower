from __future__ import annotations

import csv
import hashlib
import io
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from auth.dependencies import get_current_user
from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.cost_optimization import CostOptimizationCase, CostRecommendation, CostServiceBreakdown
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from models.user import User
from schemas.cost_optimization import CostOptimizationResponse
from services.audit_log import create_audit_log

router = APIRouter()

SERVICE_BREAKDOWN = [
    ("EC2", 100000.0, 40.0),
    ("EBS", 50000.0, 20.0),
    ("RDS", 37500.0, 15.0),
    ("S3", 25000.0, 10.0),
    ("EKS", 25000.0, 10.0),
    ("Lambda", 12500.0, 5.0),
]

RECOMMENDATIONS = [
    (
        1,
        "EC2 rightsizing and Savings Plans",
        "Review c5.xlarge-heavy fleets, rightsize underutilized instances, and evaluate Savings Plans for stable baseline usage.",
        "EC2",
        20.0,
        20000.0,
        "Medium",
        "Medium",
        "Estimated at 20% of EC2 spend based on 30% average CPU utilization and stable production usage.",
    ),
    (
        2,
        "Snapshot and remove unattached EBS volumes",
        "Validate last use, snapshot where required, then delete unattached EBS volumes under change approval.",
        "EBS",
        15.0,
        7500.0,
        "Low",
        "Low",
        "Estimated at 15% of EBS spend based on 200 unattached volumes and snapshot-before-delete controls.",
    ),
    (
        3,
        "Move S3 Standard data to lifecycle policies",
        "Apply Intelligent-Tiering or lifecycle transitions to non-hot S3 data after access-pattern validation.",
        "S3",
        25.0,
        6250.0,
        "Low",
        "Low",
        "Estimated at 25% of S3 spend based on 80% of 50 TB remaining in Standard storage.",
    ),
    (
        4,
        "Optimize EKS node groups",
        "Rightsize c5.xlarge node groups and evaluate autoscaling boundaries for the three EKS clusters.",
        "EKS",
        15.0,
        3750.0,
        "Medium",
        "Medium",
        "Estimated at 15% of EKS-related compute spend based on 3 clusters with 10 c5.xlarge nodes each.",
    ),
    (
        5,
        "Create snapshot retention policy",
        "Define retention limits and approval workflow for EBS snapshots to avoid uncontrolled growth.",
        "EBS",
        5.0,
        2500.0,
        "Low",
        "Low",
        "Estimated at 5% of EBS spend from reducing excessive snapshot retention while preserving recovery points.",
    ),
]


def _tenant_scope(current_user: User, tenant_id: uuid.UUID) -> None:
    if current_user.role != "ADMIN" and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")


def _fingerprint(*parts: object) -> str:
    return hashlib.sha256(":".join(str(part) for part in parts).encode()).hexdigest()


def _load_case(db: Session, tenant_id: uuid.UUID) -> CostOptimizationCase:
    case = db.scalar(
        select(CostOptimizationCase)
        .options(selectinload(CostOptimizationCase.service_breakdown), selectinload(CostOptimizationCase.recommendations))
        .where(CostOptimizationCase.tenant_id == tenant_id)
        .order_by(CostOptimizationCase.created_at.desc())
        .limit(1)
    )
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost optimization case not found")
    return case


def _response(db: Session, tenant: Tenant, case: CostOptimizationCase) -> CostOptimizationResponse:
    total_savings = sum(item.estimated_monthly_savings for item in case.recommendations)
    return CostOptimizationResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        case=case,
        estimated_monthly_savings=total_savings,
        estimated_annual_savings=total_savings * 12,
        optimized_monthly_cost=max(case.monthly_spend - total_savings, 0),
        architecture_current=["AWS Accounts", "EKS Microservices", "EC2", "EBS", "RDS", "S3", "Lambda"],
        architecture_proposed=[
            "Rightsized EC2/EKS",
            "EBS cleanup",
            "S3 lifecycle policies",
            "Savings Plans",
            "Tagging governance",
        ],
        implementation_plan=[
            "Validate utilization and ownership data.",
            "Approve non-destructive cleanup using snapshots/backups first.",
            "Apply rightsizing and lifecycle changes in staged production waves.",
            "Track savings against the explicit assumptions in this test case.",
        ],
    )


@router.get("/{tenant_id}", response_model=CostOptimizationResponse)
def get_cost_optimization(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostOptimizationResponse:
    _tenant_scope(current_user, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return _response(db, tenant, _load_case(db, tenant_id))


@router.post("/demo/clara", response_model=CostOptimizationResponse)
def seed_clara_demo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_WRITE)),
) -> CostOptimizationResponse:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == "clara-fintech"))
    if tenant is None:
        tenant = Tenant(
            name="Clara Fintech",
            slug="clara-fintech",
            industry="Fintech",
            contact_name="Clara FinOps Team",
            contact_email="finops@clara.example",
            notes="Demo AWS cost optimization tenant. Monthly AWS spend: 250000 USD.",
        )
        db.add(tenant)
        db.flush()
    else:
        tenant.industry = tenant.industry or "Fintech"
        tenant.notes = tenant.notes or "Demo AWS cost optimization tenant. Monthly AWS spend: 250000 USD."

    cloud_account = db.scalar(select(CloudAccount).where(CloudAccount.tenant_id == tenant.id, CloudAccount.name == "AWS Production"))
    if cloud_account is None:
        cloud_account = CloudAccount(
            tenant_id=tenant.id,
            provider="aws",
            name="AWS Production",
            account_id="123456789012",
            auth_type="role_arn",
            role_arn="arn:aws:iam::123456789012:role/NorthboundReadOnlyRole",
            external_id="clara-fintech-demo",
            default_region="us-east-1",
            is_active=True,
        )
        db.add(cloud_account)
        db.flush()

    existing_case_ids = db.scalars(select(CostOptimizationCase.id).where(CostOptimizationCase.tenant_id == tenant.id)).all()
    if existing_case_ids:
        db.execute(delete(CostRecommendation).where(CostRecommendation.case_id.in_(existing_case_ids)))
        db.execute(delete(CostServiceBreakdown).where(CostServiceBreakdown.case_id.in_(existing_case_ids)))
        db.execute(delete(CostOptimizationCase).where(CostOptimizationCase.id.in_(existing_case_ids)))
    case = CostOptimizationCase(
        tenant_id=tenant.id,
        provider="aws",
        monthly_spend=250000.0,
        currency="USD",
        description="Clara fintech AWS FinOps test case for microservices cost optimization.",
    )
    db.add(case)
    db.flush()
    for service_name, monthly_cost, percentage in SERVICE_BREAKDOWN:
        db.add(CostServiceBreakdown(case_id=case.id, service_name=service_name, monthly_cost=monthly_cost, percentage=percentage))
    for priority, title, description, service_name, percent, monthly_savings, effort, risk, assumptions in RECOMMENDATIONS:
        db.add(
            CostRecommendation(
                case_id=case.id,
                priority=priority,
                title=title,
                description=description,
                service_name=service_name,
                estimated_savings_percent=percent,
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=monthly_savings * 12,
                implementation_effort=effort,
                risk_level=risk,
                assumptions=assumptions,
            )
        )

    now = datetime.now(UTC)
    resource_specs = [
        ("ec2-fleet-c5xlarge", "compute", "EC2 c5.xlarge fleet summary", "running", "private", {"service": "EC2", "instance_type": "c5.xlarge", "instance_count": 500, "cpu_average_14d": 30}),
        ("ebs-unattached-volumes", "block_storage", "Unattached EBS volumes summary", "detached", "private", {"service": "EBS", "volume_count": 200, "attached_to": None}),
        ("rds-production-cluster", "database", "RDS production database tier", "running", "private", {"service": "RDS", "monthly_cost": 37500}),
        ("s3-data-lake-standard", "object_storage", "S3 data lake Standard storage", "available", "private", {"service": "S3", "storage_tb": 50, "standard_storage_percent": 80}),
        ("eks-node-groups-c5xlarge", "compute", "EKS c5.xlarge node groups", "running", "private", {"service": "EKS", "cluster_count": 3, "nodes_per_cluster": 10}),
        ("lambda-payment-jobs", "compute", "Lambda payment processing jobs", "active", "private", {"service": "Lambda", "monthly_cost": 12500}),
    ]
    for resource_id, resource_type, name, lifecycle_status, exposure, metadata in resource_specs:
        existing = db.scalar(
            select(Resource).where(Resource.tenant_id == tenant.id, Resource.cloud_account_id == cloud_account.id, Resource.resource_id == resource_id)
        )
        values = {
            "tenant_id": tenant.id,
            "cloud_account_id": cloud_account.id,
            "provider": "aws",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "fingerprint": _fingerprint(tenant.id, cloud_account.id, "aws", resource_id),
            "name": name,
            "region": "us-east-1",
            "account_id": cloud_account.account_id,
            "raw_type": metadata["service"],
            "status": lifecycle_status,
            "lifecycle_status": lifecycle_status,
            "exposure_level": exposure,
            "environment": "prod",
            "criticality": "high",
            "owner": "platform-finops",
            "cost_center": "clara-cloud",
            "application": "payments-platform",
            "service_name": str(metadata["service"]),
            "tags": {"environment": "prod", "owner": "platform-finops", "cost_center": "clara-cloud", "application": "payments-platform"},
            "metadata_json": {"provider_details": metadata, "case_study": "clara-fintech-cost-optimization"},
            "relationships": {},
            "discovered_at": now,
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            db.add(Resource(**values))

    findings = [
        ("idle_compute", "finops", "medium", "Underutilized EC2 c5.xlarge fleet", "EC2 average CPU utilization is 30%; validate rightsizing and Savings Plans.", 20000.0),
        ("unattached_volume", "finops", "medium", "200 unattached EBS volumes", "Snapshot if required, then delete unused detached EBS volumes under approval.", 7500.0),
        ("excessive_snapshots", "finops", "low", "Excessive EBS snapshot retention", "Apply retention policy after recovery point validation.", 2500.0),
        ("s3_lifecycle_optimization", "finops", "medium", "S3 Standard lifecycle opportunity", "Move eligible data to Intelligent-Tiering or lifecycle classes after access validation.", 6250.0),
        ("eks_rightsizing", "finops", "medium", "EKS node group rightsizing opportunity", "Tune c5.xlarge node groups and autoscaling ranges.", 3750.0),
        ("missing_tags", "governance", "high", "Cost allocation tag gaps", "Enforce environment, owner, cost center, and application tags.", None),
        ("observability_gap", "observability", "medium", "Monitoring coverage gaps", "Add alarms and utilization dashboards for cost-sensitive services.", None),
    ]
    for finding_type, category, severity, title, recommendation, waste in findings:
        fingerprint = _fingerprint(tenant.id, cloud_account.id, finding_type, "clara-demo")
        existing = db.scalar(select(Finding).where(Finding.fingerprint == fingerprint))
        if existing is None:
            db.add(
                Finding(
                    tenant_id=tenant.id,
                    cloud_account_id=cloud_account.id,
                    provider="aws",
                    finding_type=finding_type,
                    category=category,
                    severity=severity,
                    status="open",
                    title=title,
                    description=recommendation,
                    evidence={"case_study": "clara-fintech", "estimated": True, "monthly_aws_spend": 250000},
                    recommendation=recommendation,
                    estimated_monthly_waste=waste,
                    rule_id=f"clara_{finding_type}",
                    fingerprint=fingerprint,
                )
            )

    scores = [
        ("finops", 64, "fair", "FinOps score reflects EC2 rightsizing, EBS cleanup, S3 lifecycle, and EKS optimization opportunities."),
        ("governance", 68, "fair", "Governance score reflects missing tag controls across cost-sensitive services."),
        ("observability", 72, "fair", "Observability score reflects partial monitoring coverage over cost drivers."),
        ("security_baseline", 84, "good", "Security baseline is stable in the cost study scope."),
        ("resilience", 78, "good", "Resilience depends on snapshot retention controls and staged cleanup validation."),
        ("overall", 73, "fair", "Overall score reflects material FinOps savings potential with manageable operational risk."),
    ]
    for score_type, score_value, grade, summary in scores:
        db.add(
            CloudScore(
                tenant_id=tenant.id,
                cloud_account_id=cloud_account.id,
                provider="aws",
                score_type=score_type,
                score_value=score_value,
                grade=grade,
                trend="stable",
                summary=summary,
                evidence={"case_study": "clara-fintech", "formula_version": "demo-v1"},
            )
        )

    create_audit_log(
        db,
        tenant_id=tenant.id,
        user_id=current_user.id,
        actor_role=current_user.role,
        action="clara_demo_seeded",
        resource_type="cost_optimization_case",
        resource_id=str(case.id),
        metadata={"monthly_spend": 250000, "provider": "aws"},
    )
    db.commit()
    case = _load_case(db, tenant.id)
    return _response(db, tenant, case)


@router.get("/{tenant_id}/export.csv")
def export_cost_model_csv(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _tenant_scope(current_user, tenant_id)
    case = _load_case(db, tenant_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "service",
            "current_monthly_cost",
            "optimization_action",
            "assumed_savings_percent",
            "estimated_monthly_savings",
            "optimized_monthly_cost",
            "assumptions",
        ]
    )
    costs = {item.service_name: item.monthly_cost for item in case.service_breakdown}
    for recommendation in sorted(case.recommendations, key=lambda item: item.priority):
        current_cost = costs.get(recommendation.service_name, 0.0)
        writer.writerow(
            [
                recommendation.service_name,
                f"{current_cost:.2f}",
                recommendation.title,
                f"{recommendation.estimated_savings_percent:.2f}",
                f"{recommendation.estimated_monthly_savings:.2f}",
                f"{max(current_cost - recommendation.estimated_monthly_savings, 0):.2f}",
                recommendation.assumptions,
            ]
        )
    create_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        actor_role=current_user.role,
        action="cost_csv_exported",
        resource_type="cost_optimization_case",
        resource_id=str(case.id),
        commit=True,
    )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clara-cost-optimization.csv"'},
    )
