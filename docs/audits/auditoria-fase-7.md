# Auditoria Fase 7 - Risk Scoring Engine

## 1. Objetivo

Implementar un Risk Scoring Engine deterministico que calcule scores operativos a partir de findings existentes y recursos normalizados.

## 2. Alcance

Incluido:
- Modelo `CloudScore`.
- Migracion `cloud_scores`.
- Enums, schemas, formulas, weights, engine y service de scoring.
- Endpoints `/api/v1/scores`.
- Score history.
- Latest scores.
- Summary ejecutivo deterministico.
- Audit logging.
- Tests de formulas, engine y API/RBAC.

Fuera de alcance:
- AI analysis.
- Executive reports.
- Frontend dashboard.
- Azure/GCP.
- Kubernetes.
- Auto-remediation.
- Autonomous agents.
- Microservices.

## 3. Auditoría inicial

Phase 6 dejo findings deterministicos persistidos con severity, type, category y status. No existia persistencia historica de scores ni endpoints para consultar latest/history/summary.

Phase 7 usa findings con status `open` y `acknowledged`, excluyendo `resolved` y `false_positive`.

## 4. Plan técnico

1. Crear enums de score.
2. Crear formulas deterministicas.
3. Definir pesos globales.
4. Crear modelo `CloudScore`.
5. Crear migracion Alembic.
6. Implementar `RiskScoringEngine`.
7. Implementar service con auditoria y validacion de scope.
8. Exponer API `/api/v1/scores`.
9. Agregar tests.
10. Documentar arquitectura y auditoria.
11. Validar Docker, migraciones, tests y health checks.

## 5. Arquitectura

```text
Normalized Resources
-> Findings Engine
-> Risk Scoring Engine
-> Score Records
-> API Query Layer
-> Future Dashboard / AI Reports
```

Los scores son deterministas, explicables y auditables.

## 6. Archivos creados

- `backend/scoring/enums.py`
- `backend/scoring/schemas.py`
- `backend/scoring/formulas.py`
- `backend/scoring/weights.py`
- `backend/scoring/engine.py`
- `backend/scoring/service.py`
- `backend/models/cloud_score.py`
- `backend/api/routes/scores.py`
- `backend/alembic/versions/2026_05_11_0400-0006_risk_scoring_engine.py`
- `backend/tests/test_scoring_formulas.py`
- `backend/tests/test_scoring_engine.py`
- `backend/tests/test_scoring_api.py`
- `docs/architecture/risk-scoring-engine.md`
- `docs/audits/auditoria-fase-7.md`

## 7. Archivos modificados

- `backend/scoring/__init__.py`
- `backend/models/__init__.py`
- `backend/api/router.py`

## 8. Implementación

Scores implementados:
- FinOps Score.
- Governance Score.
- Observability Score.
- Security Baseline Score.
- Resilience Score.
- Overall Cloud Operational Score.

Formula base:
- Cada score inicia en 100.
- Findings activos descuentan puntos por severity.
- Resultado se limita a 0-100.

Deducciones:
- `critical`: 25
- `high`: 15
- `medium`: 8
- `low`: 3
- `informational`: 1

Overall:
- Weighted average de cinco dominios.

Endpoints:
- `POST /api/v1/scores/calculate`
- `GET /api/v1/scores/latest`
- `GET /api/v1/scores/history`
- `GET /api/v1/scores/summary`

## 9. Validación

Validaciones ejecutadas durante desarrollo:

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
docker compose exec backend python -m ruff check .
```

Resultados:
- Alembic aplico `0006_risk_scoring`.
- Pytest: `55 passed`.
- Ruff: `All checks passed`.

Validacion funcional API:
- Login JWT correcto con `admin@northbound.local`.
- `POST /api/v1/findings/run` ejecuto findings sobre el recurso demo existente.
- `POST /api/v1/scores/calculate` creo 6 scores.
- `GET /api/v1/scores/latest` devolvio 6 latest scores.
- `GET /api/v1/scores/summary` devolvio overall, domain scores, grades, trends y top drivers.
- `GET /api/v1/scores/history?limit=10` devolvio historial.
- Se marco un finding como `resolved`.
- Recalculo posterior mantuvo 6 scores y el overall mejoro de 89 a 93 por excluir el finding resuelto.

Validacion final esperada:

```powershell
docker compose down
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/status
```

Validacion final ejecutada:
- `docker compose down`
- `docker compose up --build -d`
- `docker compose exec backend alembic upgrade head`
- `docker compose exec backend pytest` -> `55 passed`
- `docker compose exec backend python -m ruff check .` -> `All checks passed`
- `/health` -> OK
- `/api/v1/status` -> OK

## 10. Pruebas

Cobertura agregada:
- Deducciones por severity.
- Clamp 0-100.
- Grade mapping.
- Weighted overall score.
- Trend calculation.
- Score calculation from findings.
- Exclusion de `resolved` y `false_positive`.
- Provider filter.
- Cloud account filter.
- Persistencia e historia.
- Auth requerida.
- Viewer puede leer.
- Viewer no puede calcular.
- Analyst puede calcular.
- Latest scores endpoint.
- Summary endpoint.

## 11. Seguridad

- Todos los endpoints scoring requieren JWT.
- Tenant isolation se aplica en calculate/latest/history/summary.
- ADMIN y ANALYST calculan scores.
- ADMIN, ANALYST y VIEWER leen scores.
- Evidence no incluye credenciales cloud.
- No hay AI-generated scoring.

## 12. Observabilidad

Logs estructurados:
- `Scoring calculation started`.
- `Scoring calculation completed`.
- `Scoring calculation failed`.

Campos seguros:
- `tenant_id`
- `cloud_account_id`
- `provider`
- `score_types_calculated`
- `execution_time_ms`

Audit logs:
- `scoring_calculation_started`
- `scoring_calculation_completed`
- `scoring_calculation_failed`

No se loguean payloads crudos ni evidencia completa.

## 13. Riesgos y trade-offs

- Scores dependen de la calidad de findings y metadata normalizada.
- Pesos son globales, no configurables por tenant en esta fase.
- No hay acceptance/suppression workflow todavia.
- No se generan reportes ni dashboard.
- Overall puede ser alto si solo existe una cantidad pequena de findings iniciales; esto es esperado en Phase 7.

## 14. Refactorización recomendada

- Agregar configuracion de pesos por tenant.
- Implementar risk acceptance y suppressions.
- Agregar score deltas por ventanas temporales.
- Agregar agregaciones por cloud account, provider y business unit.
- Integrar dashboard y reportes en fases posteriores.
- Permitir simulacion de impacto antes de resolver findings.

## 15. Auditoría final

Phase 7 implementa scoring deterministico sin introducir AI, reports, dashboard, Azure, GCP, Kubernetes, remediation, autonomous agents ni microservices.

Los scores se persisten historicamente, se pueden consultar como latest/history/summary y usan findings activos como fuente auditable.

## 16. Commit sugerido

```text
feat: implement deterministic risk scoring engine
```
