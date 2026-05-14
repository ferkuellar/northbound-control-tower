# Provisioning Request Workflow Audit

## Resumen ejecutivo

Phase B implementa requests persistentes de aprovisionamiento para convertir findings en borradores controlados. `nb fix plan` ya no usa memoria de proceso: crea `ProvisioningRequest` y artifacts JSON en PostgreSQL. Terraform sigue deshabilitado.

## Archivos creados/modificados

Backend:

- `backend/models/provisioning_request.py`
- `backend/provisioning/enums.py`
- `backend/provisioning/template_catalog.py`
- `backend/provisioning/service.py`
- `backend/provisioning/schemas.py`
- `backend/api/routes/provisioning.py`
- `backend/alembic/versions/2026_05_13_0500-0012_provisioning_requests.py`
- `backend/cloud_shell/services/fix_shell_service.py`
- `backend/cloud_shell/services/request_shell_service.py`
- `backend/cloud_shell/services/evidence_shell_service.py`
- `backend/tests/test_cloud_shell.py`
- `backend/api/router.py`
- `backend/models/__init__.py`

Docs:

- `docs/provisioning-request-workflow.md`
- `docs/audits/provisioning-request-workflow-audit.md`

## Validaciones realizadas

- `python -m py_compile backend\models\provisioning_request.py backend\provisioning\service.py backend\api\routes\provisioning.py backend\tests\test_cloud_shell.py`
- `cd frontend && npm run lint`
- `docker compose up --build -d backend worker`
- `docker compose exec backend alembic upgrade head`
- `docker compose exec backend pytest`
- `curl http://localhost:8000/health`
- `curl http://localhost:8000/api/v1/status`

Resultado:

- Backend health: OK.
- API status: OK.
- Pytest backend: `94 passed, 2 warnings`.

## Pruebas ejecutadas

Se agregaron pruebas para:

- `nb fix plan` persiste request y artifacts.
- `nb requests show` lee request persistente.
- `nb evidence show` lista artifacts persistentes.

La suite completa backend pasó con 94 pruebas.

## Riesgos identificados

- Request numbering es suficiente para MVP local, no para alta concurrencia.
- Artifacts siguen en DB; futura migración a object storage será necesaria.
- No existe workflow de approval real.
- No se crea workspace Terraform todavía.

## Controles implementados

- Tenant isolation en servicio y endpoints.
- RBAC por permisos existentes.
- No ejecución Terraform.
- No cloud API calls.
- Artifacts no incluyen credenciales.
- Evidence marca explícitamente que Terraform está deshabilitado.

## Limitaciones actuales

- No `terraform init`.
- No `terraform validate`.
- No `terraform plan`.
- No approval workflow.
- No apply.
- No post-remediation validation.

## Recomendaciones siguiente fase

Phase C — Terraform Validate and Plan:

- Crear workspace seguro por request.
- Materializar `terraform.tfvars.json`.
- Ejecutar `terraform init` y `terraform validate`.
- Ejecutar `terraform plan -out=plan.out`.
- Convertir plan a JSON.
- Persistir artifacts y checksums.
- Mantener apply deshabilitado.

## Commit sugerido

`feat: add provisioning request workflow foundation`
