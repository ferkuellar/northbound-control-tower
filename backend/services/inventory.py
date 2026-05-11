from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from collectors.aws.collector import AWSInventoryCollector
from collectors.oci.collector import OCIInventoryCollector
from core.config import settings
from models.cloud_account import CloudAccount, CloudProvider
from models.inventory_scan import InventoryScan, InventoryScanStatus
from models.resource import Resource
from models.user import User
from normalization.service import ResourceNormalizationService
from services.audit_log import create_audit_log

logger = logging.getLogger(__name__)
normalization_service = ResourceNormalizationService()


def create_inventory_scan(db: Session, *, cloud_account: CloudAccount, current_user: User) -> InventoryScan:
    scan = InventoryScan(
        tenant_id=current_user.tenant_id,
        cloud_account_id=cloud_account.id,
        provider=cloud_account.provider,
        status=InventoryScanStatus.PENDING.value,
        created_by_user_id=current_user.id,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def upsert_resource(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    cloud_account_id: uuid.UUID,
    normalized: dict[str, Any],
) -> Resource:
    fingerprint = normalized.get("fingerprint")
    resource = None
    if fingerprint:
        resource = db.scalar(
            select(Resource).where(
                Resource.tenant_id == tenant_id,
                Resource.cloud_account_id == cloud_account_id,
                Resource.fingerprint == fingerprint,
            )
        )
    if resource is None:
        resource = db.scalar(
            select(Resource).where(
                Resource.tenant_id == tenant_id,
                Resource.cloud_account_id == cloud_account_id,
                Resource.provider == normalized["provider"],
                Resource.resource_id == normalized["resource_id"],
            )
        )
    if resource is None:
        resource = Resource(
            tenant_id=tenant_id,
            cloud_account_id=cloud_account_id,
            provider=normalized["provider"],
            resource_id=normalized["resource_id"],
        )
        db.add(resource)

    resource.resource_type = normalized["resource_category"]
    resource.name = normalized.get("name")
    resource.region = normalized.get("region")
    resource.account_id = normalized.get("account_id")
    resource.compartment_id = normalized.get("compartment_id")
    resource.availability_zone = normalized.get("availability_zone")
    resource.availability_domain = normalized.get("availability_domain")
    resource.raw_type = normalized.get("raw_type")
    resource.status = normalized.get("lifecycle_status")
    resource.lifecycle_status = normalized.get("lifecycle_status")
    resource.exposure_level = normalized.get("exposure_level")
    resource.environment = normalized.get("environment")
    resource.criticality = normalized.get("criticality")
    resource.owner = normalized.get("owner")
    resource.cost_center = normalized.get("cost_center")
    resource.application = normalized.get("application")
    resource.service_name = normalized.get("service_name")
    resource.fingerprint = normalized.get("fingerprint")
    resource.tags = normalized.get("tags", {})
    resource.metadata_json = normalized.get("metadata", {})
    resource.relationships = normalized.get("relationships", {})
    resource.discovered_at = normalized.get("discovered_at", datetime.now(UTC))
    return resource


def category_counts(resources: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for resource in resources:
        category = str(resource.get("resource_category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def run_aws_inventory_scan(db: Session, *, cloud_account: CloudAccount, current_user: User) -> InventoryScan:
    scan = create_inventory_scan(db, cloud_account=cloud_account, current_user=current_user)
    logger.info(
        "AWS inventory scan started",
        extra={
            "scan_id": str(scan.id),
            "tenant_id": str(scan.tenant_id),
            "cloud_account_id": str(scan.cloud_account_id),
            "provider": scan.provider,
        },
    )
    create_audit_log(
        db,
        tenant_id=scan.tenant_id,
        user_id=current_user.id,
        action="aws_inventory_scan_started",
        resource_type="inventory_scan",
        resource_id=str(scan.id),
        metadata={"cloud_account_id": str(cloud_account.id), "provider": CloudProvider.AWS.value},
        commit=True,
    )

    scan.status = InventoryScanStatus.RUNNING.value
    db.commit()
    try:
        collector = AWSInventoryCollector(cloud_account, timeout_seconds=settings.aws_scan_timeout_seconds)
        collected_resources, partial_errors = collector.collect_all()
        normalized_resources = normalization_service.normalize_many(
            collected_resources,
            tenant_id=scan.tenant_id,
            cloud_account_id=scan.cloud_account_id,
            account_id=cloud_account.account_id,
        )
        for normalized in normalized_resources:
            upsert_resource(
                db,
                tenant_id=scan.tenant_id,
                cloud_account_id=scan.cloud_account_id,
                normalized=normalized,
            )

        scan.status = InventoryScanStatus.COMPLETED.value
        scan.completed_at = datetime.now(UTC)
        scan.resources_discovered = len(normalized_resources)
        if partial_errors:
            scan.error_message = "; ".join(error["message"] for error in partial_errors[:5])
            for error in partial_errors:
                if error["type"] == "access_denied":
                    create_audit_log(
                        db,
                        tenant_id=scan.tenant_id,
                        user_id=current_user.id,
                        action="aws_access_denied_partial",
                        resource_type="inventory_scan",
                        resource_id=str(scan.id),
                        metadata={"service": error["service"], "message": error["message"]},
                    )
        create_audit_log(
            db,
            tenant_id=scan.tenant_id,
            user_id=current_user.id,
            action="aws_inventory_scan_completed",
            resource_type="inventory_scan",
            resource_id=str(scan.id),
            metadata={
                "resources_discovered": scan.resources_discovered,
                "partial_errors": len(partial_errors),
                "categories": category_counts(normalized_resources),
            },
        )
        db.commit()
        db.refresh(scan)
        logger.info(
            "AWS inventory scan completed",
            extra={
                "scan_id": str(scan.id),
                "tenant_id": str(scan.tenant_id),
                "cloud_account_id": str(scan.cloud_account_id),
                "provider": scan.provider,
                "resources_discovered": scan.resources_discovered,
                "partial_errors": len(partial_errors),
                "categories": category_counts(normalized_resources),
            },
        )
        return scan
    except Exception as exc:
        scan.status = InventoryScanStatus.FAILED.value
        scan.completed_at = datetime.now(UTC)
        scan.error_message = str(exc)
        create_audit_log(
            db,
            tenant_id=scan.tenant_id,
            user_id=current_user.id,
            action="aws_inventory_scan_failed",
            resource_type="inventory_scan",
            resource_id=str(scan.id),
            metadata={"error": str(exc)},
        )
        db.commit()
        db.refresh(scan)
        logger.exception(
            "AWS inventory scan failed",
            extra={
                "scan_id": str(scan.id),
                "tenant_id": str(scan.tenant_id),
                "cloud_account_id": str(scan.cloud_account_id),
                "provider": scan.provider,
            },
        )
        return scan


def run_oci_inventory_scan(db: Session, *, cloud_account: CloudAccount, current_user: User) -> InventoryScan:
    scan = create_inventory_scan(db, cloud_account=cloud_account, current_user=current_user)
    logger.info(
        "OCI inventory scan started",
        extra={
            "scan_id": str(scan.id),
            "tenant_id": str(scan.tenant_id),
            "cloud_account_id": str(scan.cloud_account_id),
            "provider": scan.provider,
        },
    )
    create_audit_log(
        db,
        tenant_id=scan.tenant_id,
        user_id=current_user.id,
        action="oci_inventory_scan_started",
        resource_type="inventory_scan",
        resource_id=str(scan.id),
        metadata={"cloud_account_id": str(cloud_account.id), "provider": CloudProvider.OCI.value},
        commit=True,
    )

    scan.status = InventoryScanStatus.RUNNING.value
    db.commit()
    try:
        collector = OCIInventoryCollector(cloud_account, timeout_seconds=settings.oci_scan_timeout_seconds)
        collected_resources, partial_errors, compartment_count = collector.collect_all()
        normalized_resources = normalization_service.normalize_many(
            collected_resources,
            tenant_id=scan.tenant_id,
            cloud_account_id=scan.cloud_account_id,
            account_id=cloud_account.account_id,
        )
        for normalized in normalized_resources:
            upsert_resource(
                db,
                tenant_id=scan.tenant_id,
                cloud_account_id=scan.cloud_account_id,
                normalized=normalized,
            )

        scan.status = InventoryScanStatus.COMPLETED.value
        scan.completed_at = datetime.now(UTC)
        scan.resources_discovered = len(normalized_resources)
        if partial_errors:
            scan.error_message = "; ".join(error["message"] for error in partial_errors[:5])
            for error in partial_errors:
                if error["type"] == "access_denied":
                    create_audit_log(
                        db,
                        tenant_id=scan.tenant_id,
                        user_id=current_user.id,
                        action="oci_compartment_access_denied_partial",
                        resource_type="inventory_scan",
                        resource_id=str(scan.id),
                        metadata={
                            "service": error["service"],
                            "compartment_id": error["compartment_id"],
                            "message": error["message"],
                        },
                    )
        create_audit_log(
            db,
            tenant_id=scan.tenant_id,
            user_id=current_user.id,
            action="oci_inventory_scan_completed",
            resource_type="inventory_scan",
            resource_id=str(scan.id),
            metadata={
                "resources_discovered": scan.resources_discovered,
                "compartments_scanned": compartment_count,
                "partial_errors": len(partial_errors),
                "categories": category_counts(normalized_resources),
            },
        )
        db.commit()
        db.refresh(scan)
        logger.info(
            "OCI inventory scan completed",
            extra={
                "scan_id": str(scan.id),
                "tenant_id": str(scan.tenant_id),
                "cloud_account_id": str(scan.cloud_account_id),
                "provider": scan.provider,
                "resources_discovered": scan.resources_discovered,
                "compartments_scanned": compartment_count,
                "partial_errors": len(partial_errors),
                "categories": category_counts(normalized_resources),
            },
        )
        return scan
    except Exception as exc:
        scan.status = InventoryScanStatus.FAILED.value
        scan.completed_at = datetime.now(UTC)
        scan.error_message = str(exc)
        create_audit_log(
            db,
            tenant_id=scan.tenant_id,
            user_id=current_user.id,
            action="oci_inventory_scan_failed",
            resource_type="inventory_scan",
            resource_id=str(scan.id),
            metadata={"error": str(exc)},
        )
        db.commit()
        db.refresh(scan)
        logger.exception(
            "OCI inventory scan failed",
            extra={
                "scan_id": str(scan.id),
                "tenant_id": str(scan.tenant_id),
                "cloud_account_id": str(scan.cloud_account_id),
                "provider": scan.provider,
            },
        )
        return scan
