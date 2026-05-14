from __future__ import annotations

from enum import StrEnum


class ProvisioningRequestStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    PLAN_PENDING = "PLAN_PENDING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    FAILED = "FAILED"


class ProvisioningArtifactType(StrEnum):
    REQUEST_INPUT = "REQUEST_INPUT"
    TFVARS = "TFVARS"
    PLAN = "PLAN"
    EVIDENCE = "EVIDENCE"

