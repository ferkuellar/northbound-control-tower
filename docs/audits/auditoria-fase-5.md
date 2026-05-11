# Auditoria Fase 5 - Resource Normalization Engine

## 1. Objetivo

Construir un motor cloud-agnostic de normalizacion de recursos para que AWS y OCI persistan inventario con un modelo empresarial comun, listo para findings, scoring, reporting y analisis AI futuro.

## 2. Alcance

Incluido:
- Enums normalizados.
- Schema Pydantic `NormalizedResource`.
- Contrato `BaseProviderNormalizer`.
- Servicio `ResourceNormalizationService`.
- Normalizacion de tags AWS y OCI.
- Estandarizacion de metadata.
- Fingerprint deterministico.
- Upsert por fingerprint.
- Ampliacion del modelo `Resource`.
- Migracion Alembic.
- Tests unitarios.
- Documento de arquitectura.

Fuera de alcance:
- Findings engine.
- Risk scoring.
- Dashboard.
- AI analysis.
- Reports.
- Azure/GCP.
- Kubernetes.
- Remediation.
- Autonomous agents.
- Microservices.

## 3. Auditoría inicial

Antes de Phase 5, los collectors AWS y OCI ya emitian diccionarios normalizados de forma parcial, pero el modelo persistido seguia orientado a `resource_type/status` y deduplicaba por `resource_id`.

Riesgos detectados:
- Falta de fingerprint deterministico.
- Metadata no estandarizada.
- Tags OCI y AWS no convergian a un contrato comun.
- La plataforma downstream podia depender de detalles de provider.
- Recursos existentes no tenian campos neutrales como `exposure_level`, `environment`, `criticality` o `relationships`.

## 4. Plan técnico

1. Crear modulo `backend/normalization`.
2. Definir enums y schema unificado.
3. Implementar normalizacion de tags, metadata, lifecycle y exposure.
4. Agregar contrato base para normalizadores provider-specific.
5. Extender AWS/OCI normalizers para declarar conformidad al contrato.
6. Ampliar `Resource` y crear migracion.
7. Integrar `ResourceNormalizationService` en el upsert de inventory.
8. Agregar tests.
9. Documentar arquitectura y auditoria.
10. Validar Docker, Alembic, tests, lint y health checks.

## 5. Arquitectura

Flujo final:

```text
AWS Collector / OCI Collector
-> Provider Normalizers
-> ResourceNormalizationService
-> Unified Resource Model
-> PostgreSQL resources table
```

La logica provider-specific permanece en `collectors/aws` y `collectors/oci`. El resto de la plataforma consume recursos desde `Resource` con campos neutrales.

## 6. Archivos creados

- `backend/normalization/__init__.py`
- `backend/normalization/enums.py`
- `backend/normalization/schemas.py`
- `backend/normalization/contracts.py`
- `backend/normalization/service.py`
- `backend/normalization/validators.py`
- `backend/normalization/metadata.py`
- `backend/alembic/versions/2026_05_11_0300-0004_resource_normalization_engine.py`
- `backend/tests/test_resource_normalization_service.py`
- `backend/pytest.ini`
- `docs/architecture/resource-normalization-model.md`
- `docs/audits/auditoria-fase-5.md`

## 7. Archivos modificados

- `backend/models/resource.py`
- `backend/services/inventory.py`
- `backend/api/schemas/inventory.py`
- `backend/collectors/aws/normalizers.py`
- `backend/collectors/oci/normalizers.py`
- `backend/tests/test_aws_normalizers.py`
- `backend/tests/test_oci_normalizers.py`

## 8. Implementación

Enums implementados:
- `Provider`
- `ResourceCategory`
- `ResourceLifecycleStatus`
- `ExposureLevel`
- `Criticality`
- `Environment`

Schema implementado:
- `NormalizedResource`

Servicio implementado:
- `ResourceNormalizationService.normalize`
- `ResourceNormalizationService.normalize_many`
- `ResourceNormalizationService.normalize_tags`
- `ResourceNormalizationService.fingerprint`
- `ResourceNormalizationService.prepare_upsert_payload`

Campos agregados a `resources`:
- `fingerprint`
- `account_id`
- `compartment_id`
- `availability_domain`
- `lifecycle_status`
- `exposure_level`
- `environment`
- `criticality`
- `owner`
- `cost_center`
- `application`
- `service_name`
- `relationships`

El upsert ahora prioriza:

```text
tenant_id + cloud_account_id + fingerprint
```

y conserva fallback legacy por:

```text
tenant_id + cloud_account_id + provider + resource_id
```

## 9. Validación

Validaciones ejecutadas durante implementacion:

```powershell
docker compose exec backend python -m pytest
docker compose exec backend python -m ruff check .
docker compose exec backend alembic upgrade head
docker compose down
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/status
Invoke-RestMethod http://localhost:8000/api/v1/resources
```

Resultados:
- Pytest: `27 passed`.
- `docker compose exec backend pytest` funciona directamente con `backend/pytest.ini`.
- Ruff: `All checks passed`.
- Alembic aplico `0004_resource_norm`.
- Rebuild final con `docker compose up --build -d` levanto backend, frontend, postgres, redis, prometheus, grafana y worker.
- `/health` respondio `{"status":"ok"}`.
- `/api/v1/status` respondio `success=true`.
- `/api/v1/resources` respondio correctamente con JWT.

Limitacion de validacion funcional:
- No se ejecuto descubrimiento real AWS/OCI con recursos porque no hay credenciales cloud read-only reales configuradas en el entorno local.
- La no duplicacion queda cubierta por fingerprint deterministico y por el upsert por `tenant_id + cloud_account_id + fingerprint`.

Nota: el ID inicial de migracion excedia el limite de `alembic_version.version_num`; se corrigio a `0004_resource_norm`.

## 10. Pruebas

Cobertura agregada/ampliada:
- AWS EC2 normalization.
- AWS EBS normalization.
- AWS S3 normalization.
- AWS RDS normalization.
- AWS IAM normalization.
- AWS VPC/security group normalization.
- AWS CloudWatch alarm normalization.
- OCI compute normalization.
- OCI block volume normalization.
- OCI VCN/subnet/security list normalization.
- OCI load balancer normalization.
- OCI compartment normalization.
- OCI monitoring alarm normalization.
- AWS/OCI provider normalizer contract.
- Tag normalization.
- Metadata standardization.
- Fingerprint deterministico.
- Missing name fallback.
- Unknown resource handling.
- Secret-like metadata sanitization.

## 11. Seguridad

El motor no expone ni persiste credenciales cloud en resource metadata. Se filtran claves sensibles conocidas como:
- `secret_access_key`
- `private_key`
- `private_key_passphrase`
- `token`
- `password`
- `key_content`

Los endpoints de recursos conservan tenant isolation existente. No se agregaron endpoints publicos nuevos.

## 12. Observabilidad

Se agregaron logs estructurados para fallos de normalizacion con:
- `provider`
- `resource_id`
- `raw_type`
- `cloud_account_id`
- `tenant_id`

Los logs de finalizacion de scans incluyen conteo por categoria cuando hay recursos normalizados.

No se registran payloads crudos completos en logs.

## 13. Riesgos y trade-offs

- Recursos existentes reciben fingerprint al ser redescubiertos.
- `resource_type/status` se mantienen por compatibilidad, aunque el modelo neutral usa `resource_category/lifecycle_status`.
- La inferencia de exposure es conservadora y basada en metadata disponible.
- Relationship extraction queda minima en esta fase.
- Las pruebas funcionales con cloud real dependen de credenciales AWS/OCI read-only validas.

## 14. Refactorización recomendada

- Crear tests con mocks de collectors para validar upsert DB end-to-end sin credenciales reales.
- Extraer relationship builders por provider.
- Agregar filtros API por `resource_category`, `environment`, `criticality` y `exposure_level`.
- Backfill de fingerprints para recursos historicos si se requiere preservar datos existentes antes del siguiente scan.
- Migrar `resource_type/status` a alias formales o deprecar cuando no haya consumers legacy.

## 15. Auditoría final

Phase 5 implementa un modelo unificado sin introducir findings, scoring, dashboard, AI analysis, Azure, GCP, Kubernetes, remediation, autonomous agents ni microservices.

AWS y OCI siguen aislados en sus normalizadores provider-specific. La persistencia queda centralizada por `ResourceNormalizationService` y el upsert evita duplicados por fingerprint.

Phase 0-4 se mantienen compatibles.

## 16. Commit sugerido

```text
feat: implement cloud agnostic resource normalization engine
```
