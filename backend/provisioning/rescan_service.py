from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from findings.engine import FindingsEngine, FindingsRunSummary
from models.cloud_account import CloudAccount, CloudProvider
from models.inventory_scan import InventoryScan, InventoryScanStatus
from models.provisioning_request import CollectorRun
from models.resource import Resource
from models.user import User
from provisioning.artifact_service import sanitize_json, sanitize_sensitive_text
from services.inventory import run_aws_inventory_scan, run_oci_inventory_scan


class CollectorAdapter(Protocol):
    def run_inventory(self, db: Session, *, cloud_account: CloudAccount, current_user: User) -> InventoryScan:
        ...


class DefaultCollectorAdapter:
    def run_inventory(self, db: Session, *, cloud_account: CloudAccount, current_user: User) -> InventoryScan:
        if cloud_account.provider == CloudProvider.AWS.value:
            return run_aws_inventory_scan(db, cloud_account=cloud_account, current_user=current_user)
        if cloud_account.provider == CloudProvider.OCI.value:
            return run_oci_inventory_scan(db, cloud_account=cloud_account, current_user=current_user)
        raise ValueError(f"Unsupported provider: {cloud_account.provider}")


@dataclass(frozen=True)
class RescanResult:
    collector_run: CollectorRun
    inventory_scan: InventoryScan | None
    findings_summary: FindingsRunSummary | None
    inventory_snapshot: dict
    findings_snapshot: list[dict]
    success: bool
    error_message: str | None = None


class RescanService:
    def __init__(self, db: Session, *, collector_adapter: CollectorAdapter | None = None, findings_engine: FindingsEngine | None = None) -> None:
        self.db = db
        self.collector_adapter = collector_adapter or DefaultCollectorAdapter()
        self.findings_engine = findings_engine or FindingsEngine(db)

    def rescan_account(
        self,
        *,
        cloud_account: CloudAccount,
        current_user: User,
        trigger_source: str,
    ) -> RescanResult:
        started = datetime.now(UTC)
        timer = perf_counter()
        collector_run = CollectorRun(
            collector_run_code=f"COLRUN-{uuid.uuid4().hex[:8]}",
            cloud_account_id=cloud_account.id,
            tenant_id=cloud_account.tenant_id,
            provider=cloud_account.provider,
            region=cloud_account.region or cloud_account.default_region,
            status="RUNNING",
            started_at=started,
            triggered_by=current_user.id,
            trigger_source=trigger_source,
            resources_collected_count=0,
            findings_generated_count=0,
            metadata_json={"read_only": True},
        )
        self.db.add(collector_run)
        self.db.flush()
        inventory_scan: InventoryScan | None = None
        findings_summary: FindingsRunSummary | None = None
        error_message: str | None = None
        success = False
        try:
            inventory_scan = self.collector_adapter.run_inventory(self.db, cloud_account=cloud_account, current_user=current_user)
            if inventory_scan.status != InventoryScanStatus.COMPLETED.value:
                raise RuntimeError(inventory_scan.error_message or "Inventory scan failed")
            findings_summary = self.findings_engine.run(
                tenant_id=cloud_account.tenant_id,
                cloud_account_id=cloud_account.id,
                provider=cloud_account.provider,
                scan_id=inventory_scan.id,
            )
            success = findings_summary.rule_errors == 0
            if not success:
                error_message = f"Findings engine completed with {findings_summary.rule_errors} rule errors"
        except Exception as exc:
            success = False
            error_message = sanitize_sensitive_text(str(exc))

        finished = datetime.now(UTC)
        collector_run.finished_at = finished
        collector_run.duration_ms = int((perf_counter() - timer) * 1000)
        collector_run.status = "COMPLETED" if success else "FAILED"
        collector_run.resources_collected_count = inventory_scan.resources_discovered if inventory_scan else 0
        collector_run.findings_generated_count = (findings_summary.findings_created + findings_summary.findings_updated) if findings_summary else 0
        collector_run.error_message = error_message
        collector_run.metadata_json = sanitize_json(
            {
                "read_only": True,
                "inventory_scan_id": str(inventory_scan.id) if inventory_scan else None,
                "inventory_status": inventory_scan.status if inventory_scan else None,
                "findings_summary": self._summary_payload(findings_summary) if findings_summary else None,
            }
        )
        inventory_snapshot = self.inventory_snapshot(cloud_account)
        findings_snapshot = self.findings_snapshot(cloud_account)
        self.db.flush()
        return RescanResult(collector_run, inventory_scan, findings_summary, inventory_snapshot, findings_snapshot, success, error_message)

    def _summary_payload(self, summary: FindingsRunSummary) -> dict:
        return {
            "scan_id": str(getattr(summary, "scan_id", None)) if getattr(summary, "scan_id", None) else None,
            "tenant_id": str(getattr(summary, "tenant_id", "")),
            "cloud_account_id": str(getattr(summary, "cloud_account_id", "")) if getattr(summary, "cloud_account_id", None) else None,
            "provider": getattr(summary, "provider", None),
            "resources_evaluated": getattr(summary, "resources_evaluated", 0),
            "findings_created": getattr(summary, "findings_created", 0),
            "findings_updated": getattr(summary, "findings_updated", 0),
            "findings_by_type": getattr(summary, "findings_by_type", {}),
            "findings_by_severity": getattr(summary, "findings_by_severity", {}),
            "rule_errors": getattr(summary, "rule_errors", 0),
            "execution_time_ms": getattr(summary, "execution_time_ms", 0),
        }

    def get_account(self, *, tenant_id: uuid.UUID, identifier: str) -> CloudAccount | None:
        try:
            account_uuid = uuid.UUID(identifier)
        except ValueError:
            account_uuid = None
        statement = select(CloudAccount).where(CloudAccount.tenant_id == tenant_id, CloudAccount.is_active.is_(True))
        if account_uuid:
            statement = statement.where(CloudAccount.id == account_uuid)
        else:
            statement = statement.where((CloudAccount.account_id == identifier) | (CloudAccount.name == identifier))
        return self.db.scalar(statement)

    def inventory_snapshot(self, cloud_account: CloudAccount) -> dict:
        resources = list(
            self.db.scalars(
                select(Resource).where(Resource.tenant_id == cloud_account.tenant_id, Resource.cloud_account_id == cloud_account.id)
            )
        )
        return {
            "cloud_account_id": str(cloud_account.id),
            "provider": cloud_account.provider,
            "resources_count": len(resources),
            "resources": [
                {
                    "id": str(resource.id),
                    "resource_id": resource.resource_id,
                    "resource_type": resource.resource_type,
                    "name": resource.name,
                    "region": resource.region,
                    "status": resource.status,
                }
                for resource in resources[:500]
            ],
        }

    def findings_snapshot(self, cloud_account: CloudAccount) -> list[dict]:
        from provisioning.findings_diff_service import finding_snapshot
        from models.finding import Finding

        findings = list(
            self.db.scalars(
                select(Finding).where(Finding.tenant_id == cloud_account.tenant_id, Finding.cloud_account_id == cloud_account.id)
            )
        )
        return [finding_snapshot(finding) for finding in findings]
