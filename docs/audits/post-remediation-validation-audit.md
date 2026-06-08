# Post-Remediation Validation Audit

## Resumen ejecutivo

Phase G implementa validación posterior a remediación: rescan read-only, recalculo de findings, diff before/after, resultado final y reporte de remediación.

## Alcance implementado

- `PostRemediationValidation`
- `CollectorRun`
- Rescan orchestration
- Findings diff
- Final report
- Cloud Shell commands
- Tests mínimos
- Documentación

## Archivos creados

- `backend/provisioning/post_validation_service.py`
- `backend/provisioning/rescan_service.py`
- `backend/provisioning/findings_diff_service.py`
- `backend/provisioning/remediation_report_service.py`
- `backend/cloud_shell/services/validation_shell_service.py`
- `backend/cloud_shell/services/rescan_shell_service.py`
- `backend/cloud_shell/services/remediation_report_shell_service.py`
- `backend/alembic/versions/2026_05_14_1200-0016_post_remediation_validation.py`
- `backend/tests/test_phase_g_post_validation.py`
- `docs/post-remediation-validation.md`
- `docs/rescan-collector-orchestration.md`
- `docs/findings-diff-model.md`
- `docs/remediation-final-report.md`

## Archivos modificados

- `backend/models/provisioning_request.py`
- `backend/models/__init__.py`
- `backend/findings/enums.py`
- `backend/provisioning/enums.py`
- `backend/cloud_shell/default_registry.py`
- `backend/cloud_shell/services/help_service.py`
- `frontend/app/cloud-shell/components/CommandHelpPanel.tsx`
- `docs/cloud-shell-command-reference.md`
- `docs/provisioning-request-lifecycle.md`

## Comandos agregados

- `nb validate request <request_id>`
- `nb validate finding <finding_id>`
- `nb rescan account <account_id>`
- `nb remediation report <request_id>`

## Estados agregados

- `POST_VALIDATION_PENDING`
- `POST_VALIDATION_RUNNING`
- `POST_VALIDATION_SUCCEEDED`
- `POST_VALIDATION_FAILED`
- `REMEDIATION_RESOLVED`
- `REMEDIATION_PARTIALLY_RESOLVED`
- `REMEDIATION_STILL_OPEN`
- `REMEDIATION_VALIDATION_FAILED`
- `FINAL_REPORT_GENERATING`
- `FINAL_REPORT_READY`
- `FINAL_REPORT_FAILED`

## Artifacts agregados

- `POST_VALIDATION_RESULT_JSON`
- `POST_VALIDATION_RESULT_MARKDOWN`
- `RESCAN_LOG`
- `RESCAN_INVENTORY_SNAPSHOT_JSON`
- `FINDINGS_BEFORE_JSON`
- `FINDINGS_AFTER_JSON`
- `FINDINGS_DIFF_JSON`
- `REMEDIATION_FINAL_REPORT_MARKDOWN`
- `REMEDIATION_FINAL_REPORT_JSON`
- `COLLECTOR_RUN_METADATA`

## Modelos agregados

- `PostRemediationValidation`
- `CollectorRun`

## Pruebas ejecutadas

- `docker compose exec backend alembic upgrade head`
- `docker compose run --rm backend ruff check .`
- `docker compose run --rm backend python -m pytest tests/test_phase_g_post_validation.py -q`
- `docker compose run --rm backend python -m pytest`
- `npm run lint`
- Auditoría grep de comandos prohibidos, `shell=True`, destroy/apply unsafe y shell arbitraria.

## Resultados

- Migración `0016_post_validation` aplicada correctamente.
- Backend lint: passed.
- Phase G tests: `5 passed`.
- Backend suite: `134 passed, 2 warnings`.
- Frontend lint: passed.
- Auditoría grep: sin `shell=True` ni write actions nuevas en validación. Las coincidencias son documentación de prohibiciones, parser de bloqueo o tests que validan bloqueo.

## Riesgos encontrados

- Rescan real depende de credenciales read-only válidas.
- El findings engine actual no cierra findings automáticamente; Phase G usa `last_seen_at` para confirmar si el finding reapareció en el rescan.

## Controles implementados

- Validation solo corre después de apply exitoso.
- Apply exitoso no marca `RESOLVED`.
- Rescan usa collectors read-only.
- No se usa `shell=True`.
- No se ejecuta `terraform destroy`.
- Se guardan snapshots before/after.
- Se genera findings diff y reporte final.

## Limitaciones actuales

- Ejecución síncrona MVP.
- Sin dashboard avanzado.
- Sin paquete ejecutivo PDF.

## Recomendaciones Phase H

Agregar paquete de evidencia, reportes ejecutivos y exportación documental.

## Commit sugerido

```bash
git checkout -b feature/post-remediation-validation
git add .
git commit -m "feat: add post-remediation validation workflow"
```
