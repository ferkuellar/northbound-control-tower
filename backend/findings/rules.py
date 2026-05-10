from enum import StrEnum


class FindingType(StrEnum):
    IDLE_COMPUTE = "idle_compute"
    PUBLIC_EXPOSURE = "public_exposure"
    MISSING_TAGS = "missing_tags"
    UNATTACHED_VOLUMES = "unattached_volumes"
    OBSERVABILITY_GAPS = "observability_gaps"
