from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reports.branding import ReportBranding
from reports.enums import ReportType
from reports.errors import ReportRenderingError

TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"


class HTMLReportRenderer:
    def __init__(self) -> None:
        self.environment = Environment(
            loader=FileSystemLoader(str(TEMPLATE_ROOT)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, *, report_type: ReportType, context: dict[str, Any], branding: ReportBranding, title: str) -> str:
        template_name = {
            ReportType.EXECUTIVE: "executive/executive_report.html",
            ReportType.TECHNICAL: "technical/technical_report.html",
        }[report_type]
        try:
            template = self.environment.get_template(template_name)
            return template.render(context=context, branding=branding.as_template_data(), title=title)
        except Exception as exc:
            raise ReportRenderingError("Report template rendering failed") from exc
