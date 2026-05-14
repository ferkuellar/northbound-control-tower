# Cloud Shell Foundation Audit

## Resumen ejecutivo

Se implementó la fundación de Northbound Cloud Shell como consola controlada, no como terminal Linux libre. La consola usa `xterm.js` en `/cloud-shell`, WebSocket `/ws/cloud-shell`, parser `nb`, Command Registry, RBAC mínimo, executor facade, respuestas estructuradas y auditoría persistente.

## Archivos creados/modificados

Backend:

- `backend/cloud_shell/*`
- `backend/cloud_shell/services/*`
- `backend/models/cloud_shell_audit.py`
- `backend/alembic/versions/2026_05_13_0400-0011_cloud_shell_audit.py`
- `backend/tests/test_cloud_shell.py`
- `backend/api/main.py`
- `backend/models/__init__.py`

Frontend:

- `frontend/app/cloud-shell/page.tsx`
- `frontend/app/cloud-shell/components/TerminalPanel.tsx`
- `frontend/app/cloud-shell/components/CommandHelpPanel.tsx`
- `frontend/app/cloud-shell/components/FindingContextPanel.tsx`
- `frontend/app/cloud-shell/components/EvidencePanel.tsx`
- `frontend/components/layout/Sidebar.tsx`
- `frontend/app/globals.css`
- `frontend/package.json`
- `frontend/package-lock.json`

Docs:

- `docs/cloud-shell.md`
- `docs/cloud-shell-security-model.md`
- `docs/provisioning-console-roadmap.md`
- `docs/cloud-shell-command-reference.md`
- `docs/audits/cloud-shell-foundation-audit.md`

## Validaciones realizadas

- `python -m py_compile backend\cloud_shell\command_parser.py backend\cloud_shell\command_registry.py backend\cloud_shell\command_executor.py backend\cloud_shell\router.py backend\models\cloud_shell_audit.py`
- `python -m py_compile backend\tests\test_cloud_shell.py`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `docker compose up --build -d backend frontend worker`
- `docker compose exec backend alembic upgrade head`
- `docker compose exec backend pytest`
- `curl http://localhost:8000/health`
- `curl http://localhost:8000/api/v1/status`
- `curl -I http://localhost:3000/cloud-shell`
- Playwright smoke: `/cloud-shell` redirects unauthenticated users to `/login`.

Resultado:

- Backend health: OK.
- API status: OK.
- Frontend `/cloud-shell`: HTTP 200.
- Unauthenticated browser access redirects to login as expected.
- Pytest backend: `92 passed, 2 warnings`.

## Pruebas ejecutadas

Se agregaron pruebas para:

- parser
- registry
- authorization
- executor
- auditoría de comando exitoso
- comando desconocido sin stack trace
- rechazo de rol insuficiente

La suite completa del backend pasó con 92 pruebas.

## Riesgos identificados

- Los request stubs son memoria de proceso y no sobreviven reinicio.
- `OPERATOR` se mapea a `ANALYST` porque el sistema actual solo tiene ADMIN, ANALYST y VIEWER.
- WebSocket usa JWT vía subprotocol para evitar URL query params, pero sigue siendo material sensible en handshake; no se imprime ni se registra.
- Terraform real sigue deshabilitado.
- Docker Compose sincroniza dependencias frontend con `npm install` antes de `next dev` porque el volumen persistente `frontend_node_modules` puede quedar desactualizado al agregar paquetes.

## Controles implementados

- No shell directa.
- No comandos arbitrarios.
- Parser bloquea comandos peligrosos.
- Registry allowlist.
- RBAC por rol requerido.
- Auditoría DB para comandos recibidos, bloqueados, rechazados, exitosos o no implementados.
- Respuestas sin stack traces.
- Terraform placeholder disabled.

## Patrones de diseño aplicados

- Facade: `CloudShellExecutor`.
- Singleton: `CommandRegistry`.
- Strategy: handlers por comando.
- Factory: `build_default_registry`.
- Builder: `ShellResponseBuilder`.
- Adapter: `FindingShellAdapter`.
- Decorator: aplicado como wrappers explícitos de auth/audit/timing en executor.
- Observer: descartado en esta fase para evitar event-driven architecture prematura; se recomienda para métricas/auditoría ampliada.

## Limitaciones actuales

- No existe `ProvisioningRequest` persistente.
- No se ejecuta Terraform validate/plan/apply.
- No hay approval workflow.
- No hay evidence store real.
- No hay stream progresivo de jobs Celery.

## Recomendaciones siguiente fase

Implementar Phase B — Provisioning Request Workflow:

- Persistir `ProvisioningRequest`.
- Asociarlo a `Finding`.
- Crear catálogo de templates Terraform.
- Generar inputs validados.
- Preparar workspace aislado.
- Mantener Terraform real deshabilitado hasta Phase C.

## Commit sugerido

`feat: add controlled cloud shell foundation`
