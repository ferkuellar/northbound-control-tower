from enum import StrEnum


class FindingType(StrEnum):
    IDLE_COMPUTE = "idle_compute"
    PUBLIC_EXPOSURE = "public_exposure"
    MISSING_TAGS = "missing_tags"
    UNATTACHED_VOLUME = "unattached_volume"
    OBSERVABILITY_GAP = "observability_gap"


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class FindingStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class FindingCategory(StrEnum):
    FINOPS = "finops"
    SECURITY = "security"
    GOVERNANCE = "governance"
    OBSERVABILITY = "observability"
    RESILIENCE = "resilience"


class CloudProvider(StrEnum):
    AWS = "aws"
    OCI = "oci"
