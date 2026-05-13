from __future__ import annotations

import re

from reports.enums import ReportType
from reports.errors import ReportValidationError

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z_]{8,}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"Bearer\s+eyJ", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

MANDATORY_SECTIONS = {
    ReportType.EXECUTIVE: [
        "Cover Page",
        "Executive Summary",
        "Cloud Operational Score",
        "Findings Overview",
        "Top Risks",
        "Remediation Priorities",
        "Limitations",
    ],
    ReportType.TECHNICAL: [
        "Cover Page",
        "Technical Assessment",
        "Resource Inventory Summary",
        "Findings Detail",
        "Technical Recommendations",
        "Limitations",
    ],
}


def validate_report_html(*, title: str, html: str, report_type: ReportType) -> None:
    if not title.strip():
        raise ReportValidationError("Report title is required")
    if len(html) > 2_000_000:
        raise ReportValidationError("Generated report HTML is too large")
    lowered = html.lower()
    if "<script" in lowered or "javascript:" in lowered:
        raise ReportValidationError("Generated report contains unsafe HTML")
    for pattern in SECRET_PATTERNS:
        if pattern.search(html):
            raise ReportValidationError("Generated report appears to contain credential material")
    missing = [section for section in MANDATORY_SECTIONS[report_type] if section not in html]
    if missing:
        raise ReportValidationError(f"Generated report is missing mandatory sections: {', '.join(missing)}")
