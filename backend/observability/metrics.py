from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "route", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "route", "status_code"],
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress.",
    ["method", "route"],
)
HTTP_EXCEPTIONS_TOTAL = Counter(
    "http_exceptions_total",
    "Unhandled HTTP exceptions.",
    ["method", "route"],
)

INVENTORY_SCANS_TOTAL = Counter("inventory_scans_total", "Inventory scans by provider/status.", ["provider", "status"])
INVENTORY_SCAN_DURATION_SECONDS = Histogram("inventory_scan_duration_seconds", "Inventory scan duration.", ["provider", "status"])
INVENTORY_RESOURCES_DISCOVERED_TOTAL = Counter(
    "inventory_resources_discovered_total",
    "Inventory resources discovered.",
    ["provider"],
)
INVENTORY_SCAN_FAILURES_TOTAL = Counter("inventory_scan_failures_total", "Inventory scan failures.", ["provider"])

FINDINGS_RUNS_TOTAL = Counter("findings_runs_total", "Findings runs by provider/status.", ["provider", "status"])
FINDINGS_RUN_DURATION_SECONDS = Histogram("findings_run_duration_seconds", "Findings run duration.", ["provider", "status"])
FINDINGS_CREATED_TOTAL = Counter("findings_created_total", "Findings created.", ["provider"])
FINDINGS_UPDATED_TOTAL = Counter("findings_updated_total", "Findings updated.", ["provider"])

SCORING_RUNS_TOTAL = Counter("scoring_runs_total", "Scoring runs by provider/status.", ["provider", "status"])
SCORING_RUN_DURATION_SECONDS = Histogram("scoring_run_duration_seconds", "Scoring run duration.", ["provider", "status"])

AI_ANALYSIS_REQUESTS_TOTAL = Counter("ai_analysis_requests_total", "AI analysis requests.", ["ai_provider", "analysis_type", "status"])
AI_ANALYSIS_DURATION_SECONDS = Histogram("ai_analysis_duration_seconds", "AI analysis duration.", ["ai_provider", "analysis_type", "status"])
AI_ANALYSIS_FAILURES_TOTAL = Counter("ai_analysis_failures_total", "AI analysis failures.", ["ai_provider", "analysis_type"])

REPORTS_GENERATED_TOTAL = Counter("reports_generated_total", "Reports generated.", ["report_type", "report_format", "status"])
REPORT_GENERATION_DURATION_SECONDS = Histogram(
    "report_generation_duration_seconds",
    "Report generation duration.",
    ["report_type", "report_format", "status"],
)
REPORT_GENERATION_FAILURES_TOTAL = Counter("report_generation_failures_total", "Report generation failures.", ["report_type", "report_format"])

CELERY_TASKS_TOTAL = Counter("celery_tasks_total", "Celery tasks by name/status.", ["task_name", "status"])
CELERY_TASK_DURATION_SECONDS = Histogram("celery_task_duration_seconds", "Celery task duration.", ["task_name", "status"])


def metrics_response(request: object | None = None) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def provider_label(provider: str | None) -> str:
    return provider or "all"
