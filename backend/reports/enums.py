from enum import StrEnum


class ReportType(StrEnum):
    EXECUTIVE = "executive"
    TECHNICAL = "technical"


class ReportFormat(StrEnum):
    PDF = "pdf"
    HTML = "html"


class ReportStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"


class BrandTheme(StrEnum):
    DEFAULT = "default"
    DARK = "dark"
    ENTERPRISE_LIGHT = "enterprise_light"
