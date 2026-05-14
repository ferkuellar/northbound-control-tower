# Approval Workflow Audit

## Resumen ejecutivo

Phase E implementa aprobación humana formal para requests con gates aprobados. La fase registra decisiones y snapshots, pero mantiene `terraform apply` deshabilitado y `terraform destroy` bloqueado.

## Alcance implementado

- Modelo `ProvisioningApproval`.
- Migración Alembic 0014.
- Servicio de approvals.
- Validadores de aprobación.
- Snapshots de risk, gates, cost, security y plan.
- Checksums de artifacts aprobados.
- Comandos Cloud Shell de approvals.
- Tests mínimos.
- Documentación Markdown.

## Archivos creados

- `backend/alembic/versions/2026_05_14_1000-0014_approval_workflow.py`
- `backend/provisioning/approval_service.py`
- `backend/provisioning/approval_validators.py`
- `backend/provisioning/approval_snapshots.py`
- `backend/cloud_shell/services/approval_shell_service.py`
- `backend/tests/test_phase_e_approvals.py`
- `docs/approval-workflow.md`
- `docs/change-control-model.md`
- `docs/approval-security-model.md`
- `docs/provisioning-request-lifecycle.md`

## Archivos modificados

- `backend/models/provisioning_request.py`
- `backend/models/user.py`
- `backend/models/__init__.py`
- `backend/provisioning/enums.py`
- `backend/cloud_shell/command_parser.py`
- `backend/cloud_shell/default_registry.py`
- `backend/cloud_shell/services/help_service.py`
- `backend/cloud_shell/services/terraform_shell_service.py`
- `frontend/app/cloud-shell/components/CommandHelpPanel.tsx`
- `docs/cloud-shell-command-reference.md`

## Comandos agregados

- `nb approvals list`
- `nb approvals show <request_id>`
- `nb approve <request_id> --note "..."`
- `nb reject <request_id> --note "..."`

## Estados agregados

- `PENDING_APPROVAL`
- `APPROVED`
- `REJECTED`
- `APPROVAL_EXPIRED`

## Modelos agregados

- `ProvisioningApproval`

## Pruebas ejecutadas

- `docker compose exec backend alembic upgrade head`
- `docker compose exec backend python -m pytest tests/test_phase_e_approvals.py`
- `docker compose run --rm backend ruff check .`
- `docker compose run --rm backend python -m pytest`
- `docker compose run --rm frontend npm run lint`
- Auditoría grep de patrones prohibidos en `backend`, `docs` y `frontend`.

## Resultados

- Migración 0014 aplicada correctamente en entorno local.
- Phase E tests: 6 passed.
- Backend lint: passed.
- Backend suite: 122 passed, 2 warnings.
- Frontend lint: passed.
- Auditoría grep: sin `shell=True`; referencias a `terraform apply`/`destroy` corresponden a documentación, tests de bloqueo o comandos disabled/blocked.

## Riesgos encontrados

- La doble aprobación de producción queda modelada pero no completamente aplicada.
- La separación solicitante/aprobador queda persistida para enforcement posterior.

## Controles implementados

- RBAC `APPROVER`/`ADMIN`.
- Bloqueo de approvals inválidas.
- Artifacts mínimos obligatorios.
- Snapshots y checksums.
- Apply disabled.
- Destroy blocked.
- Sin `shell=True`.

## Limitaciones actuales

- No hay dashboard avanzado.
- No hay Slack/Teams approval.
- No hay controlled apply.
- No hay doble aprobación real completa.

## Recomendaciones Phase F

Implementar Controlled Terraform Apply solo para requests `APPROVED`, usando el `plan.out` aprobado y validando checksums antes de ejecutar.

## Commit sugerido

```bash
git checkout -b feature/approval-workflow
git add .
git commit -m "feat: add provisioning approval workflow"
```
