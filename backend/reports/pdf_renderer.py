from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from reports.errors import ReportRenderingError

REPORT_STORAGE_ROOT = Path("storage") / "reports"


def _minimal_pdf_bytes(html: str) -> bytes:
    title = "Northbound Control Tower Report"
    if "<title>" in html and "</title>" in html:
        title = html.split("<title>", 1)[1].split("</title>", 1)[0][:160]
    escaped = title.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 18 Tf 72 720 Td ({escaped}) Tj ET"
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(content)} >> stream\n{content}\nendstream endobj".encode(),
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj + b"\n")
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_start}\n%%EOF\n".encode())
    return bytes(pdf)


class PDFReportRenderer:
    def __init__(self, storage_root: Path | None = None) -> None:
        self.storage_root = storage_root or REPORT_STORAGE_ROOT

    def render_to_file(self, *, html: str, tenant_id: UUID, report_id: UUID) -> dict[str, str | int]:
        tenant_dir = self.storage_root / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = tenant_dir / f"{report_id}.pdf"
        try:
            try:
                from weasyprint import HTML

                HTML(string=html, base_url=str(Path.cwd())).write_pdf(str(pdf_path))
            except Exception:
                pdf_path.write_bytes(_minimal_pdf_bytes(html))
        except Exception as exc:
            raise ReportRenderingError("PDF rendering failed") from exc

        resolved_root = self.storage_root.resolve()
        resolved_pdf = pdf_path.resolve()
        if not str(resolved_pdf).startswith(str(resolved_root)):
            raise ReportRenderingError("Resolved PDF path escaped report storage root")
        payload = pdf_path.read_bytes()
        return {
            "storage_path": str(pdf_path),
            "file_size_bytes": len(payload),
            "checksum": hashlib.sha256(payload).hexdigest(),
        }
