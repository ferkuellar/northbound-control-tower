# Auditoria Fase 6 - Findings Engine

## 1. Objetivo

Implementar un Findings Engine deterministico sobre recursos normalizados AWS/OCI para detectar hallazgos iniciales de FinOps, seguridad, gobernanza y observabilidad.

## 2. Alcance

Incluido:
- Modelo SQLAlchemy `Finding`.
- Enums de findings.
- Schemas Pydantic.
- Contrato `BaseFindingRule`.
- Registry de reglas Phase 6.
- Engine deterministico.
- Servicio de ejecucion y status updates.
- Endpoints `/api/v1/findings`.
- Auditoria de ejecuciones y cambios de estado.
- Migracion Alembic.
- Tests unitarios, engine y API/RBAC.

Fuera de alcance:
- Risk scoring.
- AI analysis.
- Executive reports.
- Dashboard.
- Azure/GCP.
- Kubernetes.
- Auto-remediation.
- Autonomous agents.
- Microservices.

## 3. Auditoría inicial

Phase 5 dejo un modelo `Resource` normalizado con provider, categoria, lifecycle, exposure, environment, metadata, tags y fingerprint. No existia una tabla de findings ni endpoints para ejecutar reglas.

El paquete `backend/findings` tenia solo un placeholder de tipos. Fue reemplazado por un modulo completo manteniendo el alcance congelado.

## 4. Plan técnico

1. Definir enums y schema de candidatos/findings.
2. Crear modelo `Finding` e indices.
3. Implementar reglas deterministicas.
4. Crear registry de reglas Phase 6.
5. Implementar `FindingsEngine` con upsert por fingerprint.
6. Crear servicio con validacion provider/cloud account, auditoria y logs.
7. Exponer endpoints protegidos.
8. Agregar tests.
9. Documentar arquitectura y auditoria.
10. Validar Docker, Alembic, tests y health checks.

## 5. Arquitectura

```text
Normalized Resources
-> Findings Engine
-> Finding Rules
-> Finding Records
-> API Query Layer
-> Future Risk Scoring / AI Reports
```

La deteccion es deterministica. La futura capa AI podra explicar findings, pero no decidir si existen.

## 6. Archivos creados

- `backend/findings/enums.py`
- `backend/findings/schemas.py`
- `backend/findings/rules.py`
- `backend/findings/registry.py`
- `backend/findings/engine.py`
- `backend/findings/service.py`
- `backend/models/finding.py`
- `backend/api/routes/findings.py`
- `backend/alembic/versions/2026_05_11_0330-0005_findings_engine.py`
- `backend/tests/test_findings_rules.py`
- `backend/tests/test_findings_engine.py`
- `backend/tests/test_findings_api.py`
- `docs/architecture/findings-engine.md`
- `docs/audits/auditoria-fase-6.md`

## 7. Archivos modificados

- `backend/findings/__init__.py`
- `backend/models/__init__.py`
- `backend/api/router.py`

## 8. Implementación

Finding types:
- `idle_compute`
- `public_exposure`
- `missing_tags`
- `unattached_volume`
- `observability_gap`

Reglas implementadas:
- Missing Tags Rule.
- Public Exposure Rule.
- Unattached Volume Rule.
- Idle Compute Rule.
- Observability Gap Rule.

Endpoints:
- `POST /api/v1/findings/run`
- `GET /api/v1/findings`
- `GET /api/v1/findings/summary`
- `GET /api/v1/findings/{finding_id}`
- `PATCH /api/v1/findings/{finding_id}/status`

Fingerprint:

```text
tenant_id + cloud_account_id + provider + resource_id + finding_type + rule_id
```

Upsert:
- Mismo fingerprint actualiza `last_seen_at`.
- Nuevo fingerprint crea finding.
- No hay auto-resolve en Phase 6.

## 9. Validación

Validaciones ejecutadas durante desarrollo:

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
docker compose exec backend python -m ruff check .
```

Resultados:
- Alembic aplico `0005_findings_engine`.
- Pytest: `41 passed`.
- Ruff: `All checks passed`.

Validacion funcional API:
- Login JWT correcto con `admin@northbound.local`.
- Se preparo un recurso demo normalizado en el tenant local.
- `POST /api/v1/findings/run` evaluo 1 recurso y creo 3 findings.
- `GET /api/v1/findings` devolvio 3 findings.
- `GET /api/v1/findings/summary` agrupo por severity/type/category/provider/status.
- `PATCH /api/v1/findings/{finding_id}/status` actualizo un finding a `acknowledged`.
- Un segundo `POST /api/v1/findings/run` actualizo 3 findings y mantuvo total en 3, sin duplicados.

Validacion final esperada:

```powershell
docker compose down
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/status
```

## 10. Pruebas

Cobertura agregada:
- Missing tags.
- Public exposure.
- Unattached volume.
- Idle compute con metricas.
- Idle compute sin metricas.
- Observability gap.
- Engine sobre recursos AWS/OCI mezclados.
- Fingerprint deterministico.
- Upsert sin duplicados.
- Tenant isolation.
- List findings requiere auth.
- Viewer puede leer.
- Viewer no puede ejecutar.
- Analyst puede ejecutar.
- Admin puede actualizar status.

## 11. Seguridad

- Todos los endpoints findings requieren JWT.
- Tenant isolation se aplica en list/detail/status/run.
- Solo ADMIN/ANALYST ejecutan reglas.
- Solo ADMIN/ANALYST actualizan status.
- Viewer solo lee.
- Evidence no incluye secretos conocidos.
- No se loguean credenciales, API keys, JWT tokens ni payloads cloud crudos.
- Recomendacion de volumen unattached exige validar uso y snapshot antes de borrar.

## 12. Observabilidad

Logs estructurados:
- `Findings run started`.
- `Findings run completed`.
- `Findings run failed`.
- Rule evaluation failure.

Campos seguros:
- `tenant_id`
- `cloud_account_id`
- `provider`
- `resources_evaluated`
- `findings_created`
- `findings_updated`
- `rule_errors`

Audit logs:
- `findings_run_started`
- `findings_run_completed`
- `findings_run_failed`
- `finding_status_updated`

## 13. Riesgos y trade-offs

- Sin auto-resolution para evitar cerrar findings indebidamente.
- Idle compute depende de metricas que los collectors aun no producen de forma completa.
- Public exposure usa senales normalizadas y metadata disponible; puede requerir enriquecimiento posterior.
- Observability gap en prod sin metadata es conservador.
- No hay severity/risk score compuesto todavia.

## 14. Refactorización recomendada

- Agregar tabla de runs para trazabilidad historica de ejecuciones.
- Implementar auto-resolution con ventana `last_seen_at` segura.
- Agregar configuracion de required tags por tenant.
- Incorporar metricas CloudWatch/OCI Monitoring reales para idle compute.
- Agregar filtros paginados y ordenamiento avanzado.
- Crear suppressions/exception workflow.

## 15. Auditoría final

Phase 6 implementa un Findings Engine deterministico y limitado al alcance definido. No introduce risk scoring, AI, reports, dashboard, Azure, GCP, Kubernetes, remediation, autonomous agents ni microservices.

El engine opera sobre recursos normalizados y persiste findings con fingerprint estable para evitar duplicados. La API permite ejecutar, listar, resumir, leer detalle y actualizar estado con RBAC basico y tenant isolation.

## 16. Commit sugerido

```text
feat: implement deterministic findings engine
```
