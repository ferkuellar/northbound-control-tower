# Reporting Engine

## Purpose

The Phase 10 reporting engine generates enterprise-grade HTML and PDF reports from deterministic Northbound Control Tower data and validated AI analysis. Reports are intended for executive review and technical assessment workflows.

## Report Generation Flow

Resources, findings, scores, and completed AI analyses are loaded through the `ReportContextBuilder`. The context is sanitized and passed to Jinja2 templates. Generated HTML is validated before persistence. PDF reports are rendered from the validated HTML and stored as local artifacts.

Flow:

Resources + Findings + Scores + AI Analyses -> Report Context Builder -> HTML Template Engine -> PDF Renderer -> Stored Report Artifact -> Download API

## HTML Rendering

HTML reports use Jinja2 templates:

- `executive/executive_report.html`
- `technical/technical_report.html`

Templates use autoescaping and avoid rendering unsafe HTML from API or AI content. Evidence is rendered as escaped JSON.

## PDF Rendering

PDF generation uses WeasyPrint. Artifacts are written to:

`storage/reports/{tenant_id}/{report_id}.pdf`

PDF binaries are not stored in the database. The database stores metadata, checksum, storage path, and optional HTML content for preview.

## Branding Model

Branding supports company name, optional logo URL placeholder, primary and secondary colors, footer text, generated-by text, and theme enum. The default brand is Northbound Control Tower.

File uploads and tenant-level persisted branding are intentionally out of scope for Phase 10.

## AI Integration

Reports include the latest completed AI analysis when available:

- Executive reports prefer executive summary or full assessment.
- Technical reports prefer technical assessment or full assessment.

If no AI analysis exists, reports still generate and include a limitation notice.

## Security Considerations

- All report endpoints require JWT.
- Tenant isolation is enforced for generation, listing, metadata, preview, and download.
- Cloud credentials, API keys, JWTs, private keys, tokens, passphrases, and sensitive evidence keys are removed from context.
- Generated HTML is validated for secret patterns and unsafe script content.
- PDF paths are deterministic and scoped below `storage/reports`.
- PDF binary content is not stored in PostgreSQL.

## Known Limitations

- Reports are generated synchronously.
- Reports are stored locally, not in object storage.
- No scheduled reports or email delivery exist in Phase 10.
- WeasyPrint runtime issues fall back to a minimal valid PDF artifact for local development continuity.

## Future Improvements

- Move report generation to Celery jobs.
- Add object storage support.
- Add tenant-level branding management.
- Add scheduled reports and email delivery.
- Add richer PDF pagination and visual charts.
- Add dashboard UI for report generation and downloads.
