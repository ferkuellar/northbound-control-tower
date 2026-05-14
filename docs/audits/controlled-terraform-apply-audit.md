# Controlled Terraform Apply Audit

## Resumen ejecutivo

Phase F implementa `terraform apply` controlado solo para requests aprobadas, usando exclusivamente `plan.out`, validando checksums, lock de ejecución y evidencia obligatoria.

## Alcance implementado

- Apply prechecks.
- Checksum verification.
- Execution lock por request.
- Terraform apply allowlisted.
- Terraform output capture.
- Cloud Shell commands.
- Tests mínimos.
- Documentación.

## Archivos creados

- `backend/alembic/versions/2026_05_14_1100-0015_controlled_terraform_apply.py`
- `backend/provisioning/checksum_service.py`
- `backend/provisioning/apply_lock_service.py`
- `backend/provisioning/apply_precheck_service.py`
- `backend/provisioning/terraform_apply_service.py`
- `backend/provisioning/output_service.py`
- `backend/cloud_shell/services/outputs_shell_service.py`
- `backend/tests/test_phase_f_apply.py`
- `docs/controlled-terraform-apply.md`
- `docs/apply-precheck-model.md`
- `docs/apply-evidence-model.md`
- `docs/terraform-output-handling.md`

## Archivos modificados

- `backend/models/provisioning_request.py`
- `backend/models/__init__.py`
- `backend/provisioning/enums.py`
- `backend/cloud_shell/default_registry.py`
- `backend/cloud_shell/services/terraform_shell_service.py`
- `backend/cloud_shell/services/help_service.py`
- `frontend/app/cloud-shell/components/CommandHelpPanel.tsx`
- `docs/cloud-shell-command-reference.md`
- `docs/provisioning-request-lifecycle.md`

## Comandos agregados

- `nb terraform apply <request_id>`
- `nb outputs show <request_id>`

## Estados agregados

- `APPLY_PRECHECK_RUNNING`
- `APPLY_PRECHECK_FAILED`
- `APPLY_READY`
- `APPLY_RUNNING`
- `APPLY_SUCCEEDED`
- `APPLY_FAILED`
- `OUTPUTS_CAPTURE_RUNNING`
- `OUTPUTS_CAPTURE_FAILED`
- `OUTPUTS_CAPTURED`

## Artifacts agregados

- `TERRAFORM_APPLY_LOG`
- `TERRAFORM_OUTPUT_JSON`
- `TERRAFORM_APPLY_METADATA`
- `TERRAFORM_APPLY_PRECHECK_RESULT`

## Pruebas ejecutadas

- `docker compose exec backend alembic upgrade head`
- `docker compose run --rm backend ruff check .`
- `docker compose run --rm backend python -m pytest`
- `npm ci`
- `npm run lint`
- Auditoría grep de comandos prohibidos, `shell=True` y destroy/apply unsafe.

## Resultados

- Migración `0015_controlled_apply` aplicada correctamente.
- Backend lint: passed.
- Backend tests: `129 passed, 2 warnings`.
- Frontend lint: passed.
- `npm ci` reportó 4 vulnerabilidades de dependencias frontend, 2 low y 2 moderate, no introducidas por Phase F.
- Auditoría grep: sin `shell=True` ni comandos Terraform/AWS peligrosos nuevos. Las coincidencias son documentación de prohibiciones, parser de bloqueo o tests de bloqueo.

## Riesgos encontrados

- Apply real depende de que Terraform esté instalado en el worker/backend.
- Phase G aún no valida si el finding fue corregido.
- Dependencias frontend reportan 4 vulnerabilidades low/moderate en `npm audit`.

## Controles implementados

- Apply solo contra `plan.out`.
- Sin `-auto-approve`.
- Sin `shell=True`.
- Checksum verification.
- Execution lock con expiración.
- Logs sanitizados.
- Outputs sensibles redacted.
- Destroy sigue bloqueado.

## Limitaciones actuales

- Apply se ejecuta síncrono para MVP.
- Celery puede envolver el servicio en una fase posterior sin cambiar el modelo de prechecks/evidence.
- No hay rollback automático.
- No hay post-remediation validation.

## Recomendaciones Phase G

Agregar rescan de cuenta, collectors, recalculo de findings y reporte final de remediación.

## Commit sugerido

```bash
git checkout -b feature/controlled-terraform-apply
git add .
git commit -m "feat: add controlled terraform apply workflow"
```
