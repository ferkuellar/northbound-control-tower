class ReportingError(Exception):
    """Base error for reporting failures."""


class ReportValidationError(ReportingError):
    """Raised when a report fails safety validation."""


class ReportRenderingError(ReportingError):
    """Raised when HTML or PDF rendering fails."""
