from enum import StrEnum


class Provider(StrEnum):
    AWS = "aws"
    OCI = "oci"


class ResourceCategory(StrEnum):
    COMPUTE = "compute"
    BLOCK_STORAGE = "block_storage"
    OBJECT_STORAGE = "object_storage"
    DATABASE = "database"
    NETWORK = "network"
    IDENTITY = "identity"
    MONITORING = "monitoring"
    SECURITY = "security"
    UNKNOWN = "unknown"


class ResourceLifecycleStatus(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"
    AVAILABLE = "available"
    ATTACHED = "attached"
    DETACHED = "detached"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class ExposureLevel(StrEnum):
    PRIVATE = "private"
    INTERNAL = "internal"
    PUBLIC = "public"
    UNKNOWN = "unknown"


class Criticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class Environment(StrEnum):
    PROD = "prod"
    DEV = "dev"
    QA = "qa"
    TEST = "test"
    SANDBOX = "sandbox"
    SHARED = "shared"
    UNKNOWN = "unknown"
