from __future__ import annotations

import json
from typing import Any


CRITICAL_PATTERNS = (
    "public access",
    "publicly accessible",
    "no encryption",
    "unencrypted",
    "unrestricted ingress",
    "0.0.0.0/0",
    "iam wildcard",
    "administratoraccess",
    "disabled logging",
)
HIGH_PATTERNS = (
    "weak network",
    "missing encryption",
    "encryption",
    "missing monitoring",
    "logging",
)
MEDIUM_PATTERNS = (
    "missing tags",
    "tag",
    "lifecycle",
    "backup",
)


SEVERITY_ORDER = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


class CheckovParser:
    def parse_text(self, value: str) -> dict[str, Any]:
        if not value.strip():
            return self._empty_summary()
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Checkov JSON is invalid.") from exc
        return self.parse(payload)

    def parse(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return self._empty_summary()

        results = payload.get("results") if isinstance(payload, dict) else None
        if isinstance(results, dict):
            passed_checks = results.get("passed_checks") or []
            failed_checks = results.get("failed_checks") or []
            skipped_checks = results.get("skipped_checks") or []
        else:
            passed_checks = payload.get("passed_checks") or []
            failed_checks = payload.get("failed_checks") or []
            skipped_checks = payload.get("skipped_checks") or []

        parsed_failed = [self._parse_failed_check(item) for item in failed_checks if isinstance(item, dict)]
        highest = self._highest_severity(parsed_failed)
        blocking_count = sum(1 for item in parsed_failed if item["severity"] in {"CRITICAL", "HIGH"})

        return {
            "passed_count": len(passed_checks),
            "failed_count": len(failed_checks),
            "skipped_count": len(skipped_checks),
            "failed_checks": parsed_failed,
            "highest_severity": highest,
            "blocking_findings_count": blocking_count,
        }

    def _empty_summary(self) -> dict[str, Any]:
        return {
            "passed_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "failed_checks": [],
            "highest_severity": "UNKNOWN",
            "blocking_findings_count": 0,
        }

    def _parse_failed_check(self, item: dict[str, Any]) -> dict[str, Any]:
        check_name = str(item.get("check_name") or "")
        check_id = str(item.get("check_id") or "")
        guideline = str(item.get("guideline") or "")
        severity = self._severity(item, check_name=check_name, check_id=check_id, guideline=guideline)
        return {
            "resource": item.get("resource") or item.get("resource_address"),
            "check_id": check_id,
            "check_name": check_name,
            "severity": severity,
            "guideline": guideline,
            "file_path": item.get("file_path") or item.get("repo_file_path"),
            "line_range": item.get("file_line_range") or item.get("line_range"),
        }

    def _severity(self, item: dict[str, Any], *, check_name: str, check_id: str, guideline: str) -> str:
        explicit = item.get("severity") or item.get("bc_check_id")
        if isinstance(explicit, str) and explicit.upper() in SEVERITY_ORDER:
            return explicit.upper()

        haystack = " ".join([check_name, check_id, guideline]).lower()
        if any(pattern in haystack for pattern in CRITICAL_PATTERNS):
            return "CRITICAL"
        if any(pattern in haystack for pattern in HIGH_PATTERNS):
            return "HIGH"
        if any(pattern in haystack for pattern in MEDIUM_PATTERNS):
            return "MEDIUM"
        if haystack.strip():
            return "UNKNOWN"
        return "UNKNOWN"

    def _highest_severity(self, failed_checks: list[dict[str, Any]]) -> str:
        highest = "UNKNOWN"
        for item in failed_checks:
            severity = str(item.get("severity") or "UNKNOWN")
            if SEVERITY_ORDER.get(severity, 0) > SEVERITY_ORDER[highest]:
                highest = severity
        return highest
