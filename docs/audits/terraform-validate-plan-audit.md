# Terraform Validate and Plan Audit

## Resumen ejecutivo

Phase C implementa Terraform validate/plan controlado desde Northbound Cloud Shell. La implementación crea workspaces aislados por request, ejecuta únicamente comandos Terraform allowlisted, genera artifacts y mantiene `apply` deshabilitado y `destroy` bloqueado.

## Alcance implementado

- Workspace Terraform por `ProvisioningRequest`.
- Template local no-op para validar el runner sin tocar cloud.
- `nb terraform validate <request_id>`.
- `nb terraform plan <request_id>`.
- `nb evidence show <request_id>` con metadata de artifacts.
- Parser de `plan.json`.
- Registro de logs, checksums y paths.
- Redacción básica de secretos.

## Archivos creados

- `backend/provisioning/artifact_service.py`
- `backend/provisioning/terraform_workspace.py`
- `backend/provisioning/terraform_runner.py`
- `backend/provisioning/terraform_plan_parser.py`
- `backend/provisioning/tasks.py`
- `backend/cloud_shell/services/terraform_shell_service.py`
- `backend/cloud_shell/services/templates_shell_service.py`
- `backend/tests/test_terraform_validate_plan.py`
- `backend/terraform-catalog/local/noop-validation/*`
- `terraform-catalog/local/noop-validation/*`
- `docs/terraform-validate-plan.md`
- `docs/terraform-runner-security.md`
- `docs/provisioning-evidence-model.md`
- `docs/audits/terraform-validate-plan-audit.md`

## Archivos modificados

- `.gitignore`
- `backend/Dockerfile`
- `backend/provisioning/enums.py`
- `backend/provisioning/service.py`
- `backend/provisioning/template_catalog.py`
- `backend/models/provisioning_request.py`
- `backend/cloud_shell/default_registry.py`
- `backend/cloud_shell/services/evidence_shell_service.py`
- `backend/tests/test_cloud_shell.py`
- `docs/cloud-shell-command-reference.md`

## Comandos agregados

- `nb templates list`
- `nb templates show <template_id>`
- `nb terraform validate <request_id>`
- `nb terraform plan <request_id>`

## Pruebas ejecutadas

```text
docker compose exec backend alembic upgrade head
docker compose exec backend pytest tests/test_cloud_shell.py tests/test_terraform_validate_plan.py
docker compose exec backend pytest
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
docker compose up --build -d
docker compose exec backend terraform version
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/status
```

Resultado focalizado:

```text
17 passed
```

Resultado completo:

```text
101 passed, 2 warnings
frontend lint: passed
frontend build: passed
terraform version: Terraform v1.9.8
/health: {"status":"ok"}
/api/v1/status: success true
```

## Resultados

La prueba focalizada valida parser, registry, autorización, workspace, artifacts, runner, missing Terraform CLI, plan parser y comandos de Cloud Shell.

## Riesgos encontrados

- El entorno backend Docker solo monta `./backend:/app`, por lo que el catálogo Terraform operativo también se incluyó en `backend/terraform-catalog`.
- Si Terraform no está disponible fuera de Docker, el runner falla de forma limpia con mensaje accionable. La imagen backend/worker ahora instala Terraform v1.9.8 para demos locales.

## Controles implementados

- No `shell=True`.
- Comandos Terraform allowlisted.
- `apply` deshabilitado.
- `destroy` bloqueado por parser.
- Workspaces con validación anti path traversal.
- Redacción básica de secretos.
- Checksums SHA-256 para artifacts.

## Limitaciones actuales

- Sin Checkov.
- Sin Infracost.
- Sin approval workflow.
- Sin apply controlado.
- Artifact storage local solamente.

## Recomendaciones Phase D

Agregar `nb security scan <request_id>`, `nb cost estimate <request_id>` y `nb risk summary <request_id>` con Checkov e Infracost antes de cualquier flujo de aprobación.

## Commit sugerido

```bash
git checkout -b feature/terraform-validate-plan
git add .
git commit -m "feat: add terraform validate and plan workflow"
```
